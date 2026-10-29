"""
Unified Command-Line Interface (CLI) for Industrial Energy Intelligence.

Commands:
  generate    Generate deterministic synthetic data (starter or full scale)
  validate    Run validation checks on primary keys, foreign keys, arithmetic, duplicates
  correlate   Run energy waste, peak demand, and SEC correlation engine
  evaluate    Benchmark validation & correlation engine against isolated ground truth
  dashboard   Generate self-contained interactive operations dashboard
  reproduce   Demonstrate 100% reproducibility by generating twice and comparing checksums
  export-dict Export human-readable Markdown and CSV data dictionaries
"""

import argparse
import sys
import os
import json
import csv
import hashlib
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from industrial_energy.generator import IndustrialDataGenerator
from industrial_energy.validator import DataValidator, generate_validation_summary_markdown
from industrial_energy.correlation_engine import CorrelationEngine
from industrial_energy.recommendation_engine import RecommendationEngine
from industrial_energy.evaluation import Evaluator, generate_evaluation_summary_markdown
from industrial_energy.dashboard import save_dashboard_file
from industrial_energy.data_dictionary import export_data_dictionary_markdown, export_data_dictionary_csv

def load_data_from_dir(data_dir: str):
    """Loads all CSV tables and ground_truth from directory into dictionary."""
    p = Path(data_dir)
    data = {}
    for csv_file in p.glob("*.csv"):
        entity_name = csv_file.stem
        records = []
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(row)
        data[entity_name] = records

    # Ground truth
    gt_file = p / "ground_truth.json"
    if gt_file.exists():
        with open(gt_file, "r", encoding="utf-8") as f:
            data["GroundTruth"] = json.load(f)
    elif "GroundTruth" in data:
        pass
    else:
        data["GroundTruth"] = []

    return data

def cmd_generate(args):
    print(f">> Generating Industrial Energy Dataset [Scale: {args.scale}, Seed: {args.seed}]...")
    gen = IndustrialDataGenerator(seed=args.seed, scale=args.scale)
    manifest = gen.export_to_directory(args.output_dir)
    print(f"[OK] Generated dataset successfully in: {args.output_dir}")
    print("Row counts:")
    for entity, count in manifest["row_counts"].items():
        print(f"  - {entity:25s}: {count:,}")
    return 0

def cmd_validate(args):
    print(f">> Validating dataset in {args.data_dir}...")
    data = load_data_from_dir(args.data_dir)
    validator = DataValidator(data)
    report = validator.validate_all()
    md = generate_validation_summary_markdown(report)
    
    if args.export_report:
        with open(args.export_report, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"[REPORT] Validation report written to: {args.export_report}")

    print(f"Status: {'PASS' if report['passed'] else 'FAIL (Negative Edge Cases Detected)'}")
    print(f"Errors: {report['total_errors']} | Warnings: {report['total_warnings']}")
    for err in report["errors"]:
        print(f"  [FAIL] [{err['rule']}] {err['message']}")
    return 0 if report["passed"] else 1

def cmd_correlate(args):
    print(f">> Correlating telemetry, production, tariffs, and weather in {args.data_dir}...")
    data = load_data_from_dir(args.data_dir)
    corr = CorrelationEngine(data)
    results = corr.analyze_all()
    
    rec_engine = RecommendationEngine(data, results)
    recommendations = rec_engine.generate_recommendations()

    print("\n--- Correlation Results ---")
    print(f"Idle Baseload Waste Detections : {len(results['idle_waste'])}")
    print(f"Total Idle Energy Wasted      : {results['metrics']['total_idle_waste_kwh']:,.1f} kWh")
    print(f"Total Idle Financial Loss     : ${results['metrics']['total_idle_waste_cost_usd']:,.2f}")
    print(f"Peak Demand Breach Events     : {results['metrics']['peak_breach_count']}")
    print(f"Highest Peak Observed         : {results['metrics']['highest_peak_kw']:,.1f} kW")
    print(f"Batches Analyzed (SEC)        : {results['metrics']['batches_analyzed']}")
    print(f"Telemetry Exceptions Handled  : {results['metrics'].get('exceptions_handled_count', 0)}")
    
    print(f"\n--- Generated Actionable Recommendations ({len(recommendations)}) ---")
    for r in recommendations:
        d = r if isinstance(r, dict) else r.__dict__
        print(f"[{d['recommendation_id']}] ({d['action_actor']}) {d['title']}")
        print(f"   Savings: {d['estimated_kwh_savings']:,.1f} kWh | ${d['estimated_cost_savings']:,.2f} | Payback: {d['payback_period_days']:.0f} days")

    return 0

def cmd_evaluate(args):
    print(f">> Benchmarking against ground truth in {args.data_dir}...")
    data = load_data_from_dir(args.data_dir)
    validator = DataValidator(data)
    val_report = validator.validate_all()

    corr = CorrelationEngine(data)
    corr_results = corr.analyze_all()

    ground_truth = data.get("GroundTruth", [])
    evaluator = Evaluator(ground_truth, val_report, corr_results)
    benchmark = evaluator.evaluate()

    md = generate_evaluation_summary_markdown(benchmark)
    if args.export_report:
        with open(args.export_report, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"[REPORT] Evaluation report written to: {args.export_report}")

    m = benchmark["metrics"]
    print("\n--- Benchmark Metrics vs Ground Truth ---")
    print(f"Ground Truth Anomalies : {m['ground_truth_total']}")
    print(f"True Positives (TP)    : {m['true_positives']}")
    print(f"False Positives (FP)   : {m['false_positives']}")
    print(f"False Negatives (FN)   : {m['false_negatives']}")
    print(f"Precision              : {m['precision'] * 100:.1f}%")
    print(f"Recall                 : {m['recall'] * 100:.1f}%")
    print(f"F1-Score               : {m['f1_score'] * 100:.1f}%")
    return 0

def cmd_dashboard(args):
    print(f">> Generating Operations Dashboard from {args.data_dir}...")
    data = load_data_from_dir(args.data_dir)
    
    val_report = DataValidator(data).validate_all()
    corr_results = CorrelationEngine(data).analyze_all()
    recs = RecommendationEngine(data, corr_results).generate_recommendations()
    bench = Evaluator(data.get("GroundTruth", []), val_report, corr_results).evaluate()

    manifest_file = Path(args.data_dir) / "manifest.json"
    manifest = {}
    if manifest_file.exists():
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)

    out_file = save_dashboard_file(
        args.output,
        manifest,
        val_report,
        corr_results,
        recs,
        bench
    )
    print(f"[OK] Dashboard generated successfully: {out_file}")

    if args.serve:
        import http.server
        import socketserver
        import webbrowser
        os.chdir(Path(out_file).parent)
        handler = http.server.SimpleHTTPRequestHandler
        port = args.port
        print(f"[SERVER] Serving dashboard at http://localhost:{port}/{Path(out_file).name} (Ctrl+C to stop)...")
        with socketserver.TCPServer(("", port), handler) as httpd:
            httpd.serve_forever()

    return 0

def cmd_reproduce(args):
    """
    Step 10: Regenerate twice with the same seed and compare row counts & SHA256 checksums
    to strictly demonstrate 100% reproducibility.
    """
    print(f">> Running Reproducibility Test [Scale: {args.scale}, Seed: {args.seed}]...")
    import tempfile
    import shutil

    dir1 = Path("temp_run_1")
    dir2 = Path("temp_run_2")

    if dir1.exists(): shutil.rmtree(dir1)
    if dir2.exists(): shutil.rmtree(dir2)

    gen1 = IndustrialDataGenerator(seed=args.seed, scale=args.scale)
    gen1.export_to_directory(str(dir1))

    gen2 = IndustrialDataGenerator(seed=args.seed, scale=args.scale)
    gen2.export_to_directory(str(dir2))

    # Compare all files
    files1 = {f.name: f for f in dir1.glob("*.csv")}
    files2 = {f.name: f for f in dir2.glob("*.csv")}

    assert files1.keys() == files2.keys(), "File list mismatch between runs!"

    print("\nComparing SHA256 Hashes across both runs:")
    all_match = True
    for name in sorted(files1.keys()):
        h1 = hashlib.sha256(files1[name].read_bytes()).hexdigest()
        h2 = hashlib.sha256(files2[name].read_bytes()).hexdigest()
        match = (h1 == h2)
        if not match:
            all_match = False
        print(f"  {'[MATCH]' if match else '[DIFF] '} {name:25s} Run1: {h1[:12]}... | Run2: {h2[:12]}...")

    # Clean up
    shutil.rmtree(dir1)
    shutil.rmtree(dir2)

    if all_match:
        print("\n[SUCCESS] 100% Reproducibility Verified! Identical byte-for-byte output across independent runs.")
        return 0
    else:
        print("\n[FAIL] Reproducibility failure detected.")
        return 1

def cmd_export_dict(args):
    print(">> Exporting data dictionary...")
    md_content = export_data_dictionary_markdown()
    csv_content = export_data_dictionary_csv()

    out_md = Path(args.output_dir) / "data_dictionary.md"
    out_csv = Path(args.output_dir) / "data_dictionary.csv"
    out_md.parent.mkdir(parents=True, exist_ok=True)

    with open(out_md, "w", encoding="utf-8") as f:
        f.write(md_content)
    with open(out_csv, "w", encoding="utf-8") as f:
        f.write(csv_content)

    print(f"[OK] Data dictionary exported:\n  - {out_md}\n  - {out_csv}")
    return 0

def main():
    parser = argparse.ArgumentParser(description="Industrial Energy Intelligence CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Generate
    p_gen = subparsers.add_parser("generate", help="Generate synthetic data")
    p_gen.add_argument("--scale", choices=["starter", "full"], default="starter", help="Dataset volume scale")
    p_gen.add_argument("--seed", type=int, default=20261022, help="Random seed for reproducibility")
    p_gen.add_argument("--output-dir", default="data/starter", help="Destination folder")
    p_gen.set_defaults(func=cmd_generate)

    # Validate
    p_val = subparsers.add_parser("validate", help="Run data validation suite")
    p_val.add_argument("--data-dir", default="data/starter", help="Directory containing dataset CSVs")
    p_val.add_argument("--export-report", default=None, help="Path to write validation markdown report")
    p_val.set_defaults(func=cmd_validate)

    # Correlate
    p_corr = subparsers.add_parser("correlate", help="Run energy waste and peak demand correlation")
    p_corr.add_argument("--data-dir", default="data/starter", help="Directory containing dataset CSVs")
    p_corr.set_defaults(func=cmd_correlate)

    # Evaluate
    p_eval = subparsers.add_parser("evaluate", help="Benchmark against ground truth")
    p_eval.add_argument("--data-dir", default="data/starter", help="Directory containing dataset CSVs")
    p_eval.add_argument("--export-report", default=None, help="Path to write evaluation markdown report")
    p_eval.set_defaults(func=cmd_evaluate)

    # Dashboard
    p_dash = subparsers.add_parser("dashboard", help="Generate interactive operations dashboard")
    p_dash.add_argument("--data-dir", default="data/starter", help="Directory containing dataset CSVs")
    p_dash.add_argument("--output", default="dashboard.html", help="Output HTML file path")
    p_dash.add_argument("--serve", action="store_true", help="Launch local preview server")
    p_dash.add_argument("--port", type=int, default=8080, help="Server port")
    p_dash.set_defaults(func=cmd_dashboard)

    # Reproduce
    p_rep = subparsers.add_parser("reproduce", help="Test 100% deterministic reproducibility")
    p_rep.add_argument("--scale", choices=["starter", "full"], default="starter")
    p_rep.add_argument("--seed", type=int, default=20261022)
    p_rep.set_defaults(func=cmd_reproduce)

    # Export Dict
    p_dict = subparsers.add_parser("export-dict", help="Export data dictionary files")
    p_dict.add_argument("--output-dir", default="docs", help="Destination directory")
    p_dict.set_defaults(func=cmd_export_dict)

    args = parser.parse_args()
    return args.func(args)

if __name__ == "__main__":
    sys.exit(main())
