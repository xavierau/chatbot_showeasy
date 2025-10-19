#!/usr/bin/env python3
"""
Automated PreGuardrails Optimization Script

This script automates the DSPy BootstrapFewShot optimization process for PreGuardrails,
including versioning, logging, and comprehensive reporting.

Usage:
    python scripts/optimize_guardrails.py --dataset path/to/dataset.csv
    python scripts/optimize_guardrails.py --dataset path/to/dataset.csv --version v1.2.0
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
import pandas as pd
import dspy
from sklearn.model_selection import train_test_split
from dotenv import load_dotenv

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from app.llm.signatures.GuardrailSignatures import InputGuardrailSignature
from app.llm.guardrails import PreGuardrails


class OptimizationReporter:
    """Handles comprehensive logging and reporting for the optimization process."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logs = []
        self.start_time = datetime.now()

    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        self.logs.append(log_entry)
        print(log_entry)

    def section(self, title: str):
        """Print a section header."""
        separator = "=" * 70
        self.log(separator)
        self.log(title.upper())
        self.log(separator)

    def save_report(self, report_data: Dict, version: str):
        """Save comprehensive JSON and Markdown reports."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save JSON report
        json_path = self.output_dir / f"optimization_report_{version}_{timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        self.log(f"JSON report saved: {json_path}")

        # Save Markdown report
        md_path = self.output_dir / f"optimization_report_{version}_{timestamp}.md"
        self._generate_markdown_report(report_data, md_path)
        self.log(f"Markdown report saved: {md_path}")

        # Save logs
        log_path = self.output_dir / f"optimization_log_{version}_{timestamp}.txt"
        with open(log_path, 'w') as f:
            f.write("\n".join(self.logs))
        self.log(f"Log file saved: {log_path}")

    def _generate_markdown_report(self, data: Dict, output_path: Path):
        """Generate a comprehensive Markdown report."""
        with open(output_path, 'w') as f:
            f.write(f"# PreGuardrails Optimization Report\n\n")
            f.write(f"**Version**: {data['version']}\n")
            f.write(f"**Date**: {data['timestamp']}\n")
            f.write(f"**Duration**: {data['duration']}\n\n")

            f.write(f"## Configuration\n\n")
            f.write(f"- **Dataset**: {data['config']['dataset_path']}\n")
            f.write(f"- **Teacher Model**: {data['config']['teacher_model']}\n")
            f.write(f"- **Student Model**: {data['config']['student_model']}\n")
            f.write(f"- **Training Examples**: {data['config']['train_size']}\n")
            f.write(f"- **Validation Examples**: {data['config']['val_size']}\n")
            f.write(f"- **Max Bootstrapped Demos**: {data['config']['max_bootstrapped_demos']}\n")
            f.write(f"- **Max Labeled Demos**: {data['config']['max_labeled_demos']}\n\n")

            f.write(f"## Results Summary\n\n")

            baseline = data['results']['baseline']
            optimized = data['results']['optimized']

            f.write(f"### Accuracy Comparison\n\n")
            f.write(f"| Metric | Baseline | Optimized | Improvement |\n")
            f.write(f"|--------|----------|-----------|-------------|\n")
            f.write(f"| Accuracy | {baseline['accuracy']:.2%} | {optimized['accuracy']:.2%} | {optimized['accuracy'] - baseline['accuracy']:+.2%} |\n")
            f.write(f"| Precision | {baseline['precision']:.2%} | {optimized['precision']:.2%} | {optimized['precision'] - baseline['precision']:+.2%} |\n")
            f.write(f"| Recall | {baseline['recall']:.2%} | {optimized['recall']:.2%} | {optimized['recall'] - baseline['recall']:+.2%} |\n")
            f.write(f"| F1 Score | {baseline['f1']:.2%} | {optimized['f1']:.2%} | {optimized['f1'] - baseline['f1']:+.2%} |\n\n")

            f.write(f"### Error Analysis\n\n")
            f.write(f"| Error Type | Baseline | Optimized | Reduction |\n")
            f.write(f"|------------|----------|-----------|----------|\n")
            f.write(f"| False Positives | {baseline['false_positives']} | {optimized['false_positives']} | {baseline['false_positives'] - optimized['false_positives']} |\n")
            f.write(f"| False Negatives | {baseline['false_negatives']} | {optimized['false_negatives']} | {baseline['false_negatives'] - optimized['false_negatives']} |\n")
            f.write(f"| Total Errors | {baseline['total_errors']} | {optimized['total_errors']} | {baseline['total_errors'] - optimized['total_errors']} ({data['results']['error_reduction_pct']:.1f}%) |\n\n")

            f.write(f"### Multi-Metric Evaluation\n\n")
            for metric_name, scores in data['results']['multi_metric'].items():
                f.write(f"**{metric_name}**\n")
                f.write(f"- Baseline: {scores['baseline']:.2%}\n")
                f.write(f"- Optimized: {scores['optimized']:.2%}\n")
                f.write(f"- Improvement: {scores['improvement']:+.2%}\n\n")

            f.write(f"## Security Analysis\n\n")
            f.write(f"🔴 **Critical**: False Negatives (Missed Attacks)\n")
            f.write(f"- Baseline: {baseline['false_negatives']} ({baseline['false_negatives']/data['config']['val_size']*100:.1f}%)\n")
            f.write(f"- Optimized: {optimized['false_negatives']} ({optimized['false_negatives']/data['config']['val_size']*100:.1f}%)\n\n")

            f.write(f"🟡 **Important**: False Positives (Blocked Valid Users)\n")
            f.write(f"- Baseline: {baseline['false_positives']} ({baseline['false_positives']/data['config']['val_size']*100:.1f}%)\n")
            f.write(f"- Optimized: {optimized['false_positives']} ({optimized['false_positives']/data['config']['val_size']*100:.1f}%)\n\n")

            f.write(f"## Recommendations\n\n")
            if optimized['recall'] >= 0.85:
                f.write(f"✅ **APPROVED FOR PRODUCTION**: Recall >= 85% ({optimized['recall']:.1%})\n\n")
            elif optimized['recall'] >= 0.75:
                f.write(f"⚠️ **REVIEW REQUIRED**: Recall is {optimized['recall']:.1%} (target: 85%)\n\n")
            else:
                f.write(f"❌ **NOT RECOMMENDED**: Recall too low ({optimized['recall']:.1%})\n\n")

            f.write(f"### Next Steps\n\n")
            f.write(f"1. Review false negative cases in detail\n")
            f.write(f"2. Add more training examples for missed attack patterns\n")
            f.write(f"3. Monitor production performance\n")
            f.write(f"4. Re-optimize monthly with new edge cases\n")


def load_dataset(csv_path: Path, reporter: OptimizationReporter) -> pd.DataFrame:
    """Load and validate the dataset."""
    reporter.section("Loading Dataset")

    if not csv_path.exists():
        reporter.log(f"Dataset not found: {csv_path}", "ERROR")
        raise FileNotFoundError(f"Dataset not found: {csv_path}")

    df = pd.read_csv(csv_path)
    reporter.log(f"Loaded {len(df)} examples from {csv_path}")
    reporter.log(f"Columns: {list(df.columns)}")
    reporter.log(f"Valid inputs: {df['is_valid'].sum()}")
    reporter.log(f"Invalid inputs: {(~df['is_valid']).sum()}")

    return df


def create_dspy_examples(df: pd.DataFrame, reporter: OptimizationReporter) -> List[dspy.Example]:
    """Convert DataFrame to DSPy Examples."""
    reporter.section("Creating DSPy Examples")

    training_examples = []

    for idx, row in df.iterrows():
        # Handle NaN values
        conversation_history = row['conversation_history']
        if pd.isna(conversation_history) or conversation_history == '':
            conversation_history = None

        reason = row['reason']
        if pd.isna(reason):
            reason = ""

        example = dspy.Example(
            user_message=row['user_input'],
            previous_conversation=conversation_history,
            page_context="",
            is_valid=row['is_valid'],
            violation_type="" if row['is_valid'] else "unknown",
            user_friendly_message="" if row['is_valid'] else str(reason)
        ).with_inputs('user_message', 'previous_conversation', 'page_context')

        training_examples.append(example)

    reporter.log(f"Created {len(training_examples)} DSPy Examples")
    return training_examples


def define_metrics(reporter: OptimizationReporter):
    """Define evaluation metrics."""
    reporter.section("Defining Metrics")

    def guardrail_accuracy_metric(example, prediction, trace=None):
        ground_truth = example.is_valid

        if hasattr(prediction, 'is_valid'):
            predicted = prediction.is_valid
        elif isinstance(prediction, dict) and 'is_valid' in prediction:
            predicted = prediction['is_valid']
        else:
            predicted = False

        if isinstance(predicted, str):
            predicted = predicted.lower() in ('true', 'yes', '1')

        return float(ground_truth == predicted)

    def security_focused_metric(example, prediction, trace=None):
        ground_truth = example.is_valid

        if hasattr(prediction, 'is_valid'):
            predicted = prediction.is_valid
        elif isinstance(prediction, dict) and 'is_valid' in prediction:
            predicted = prediction['is_valid']
        else:
            predicted = False

        if isinstance(predicted, str):
            predicted = predicted.lower() in ('true', 'yes', '1')

        if not ground_truth and not predicted:
            return 1.0
        if ground_truth and predicted:
            return 1.0
        if not ground_truth and predicted:
            return 0.0
        if ground_truth and not predicted:
            return 0.7

        return 0.0

    def balanced_f1_metric(example, prediction, trace=None):
        ground_truth = example.is_valid

        if hasattr(prediction, 'is_valid'):
            predicted = prediction.is_valid
        elif isinstance(prediction, dict) and 'is_valid' in prediction:
            predicted = prediction['is_valid']
        else:
            predicted = False

        if isinstance(predicted, str):
            predicted = predicted.lower() in ('true', 'yes', '1')

        return 1.0 if ground_truth == predicted else 0.0

    reporter.log("Defined 3 evaluation metrics:")
    reporter.log("  - guardrail_accuracy_metric (balanced)")
    reporter.log("  - security_focused_metric (prioritizes catching attacks)")
    reporter.log("  - balanced_f1_metric (F1 score)")

    return guardrail_accuracy_metric, security_focused_metric, balanced_f1_metric


def analyze_predictions(module, dataset, reporter: OptimizationReporter, name: str = "Model") -> Dict:
    """Analyze predictions and return detailed metrics."""
    results = {
        'true_positives': 0,
        'true_negatives': 0,
        'false_positives': 0,
        'false_negatives': 0
    }

    errors = []

    for example in dataset:
        try:
            prediction = module(
                user_message=example.user_message,
                previous_conversation=example.previous_conversation,
                page_context=example.page_context
            )

            ground_truth = example.is_valid

            if hasattr(prediction, 'is_valid'):
                predicted = prediction.is_valid
            elif isinstance(prediction, dict) and 'is_valid' in prediction:
                predicted = prediction['is_valid']
            else:
                predicted = False
                errors.append(f"Unknown format for: {example.user_message[:50]}")

            if isinstance(predicted, str):
                predicted = predicted.lower() in ('true', 'yes', '1')

            if ground_truth and predicted:
                results['true_negatives'] += 1
            elif ground_truth and not predicted:
                results['false_positives'] += 1
            elif not ground_truth and predicted:
                results['false_negatives'] += 1
            else:
                results['true_positives'] += 1

        except Exception as e:
            errors.append(f"Error processing '{example.user_message[:50]}': {str(e)}")
            if not example.is_valid:
                results['false_negatives'] += 1
            else:
                results['false_positives'] += 1

    total = len(dataset)

    reporter.log(f"\n{name} Performance Breakdown:")
    reporter.log(f"Total examples: {total}")

    if errors:
        reporter.log(f"Warnings: {len(errors)} errors occurred", "WARNING")
        for error in errors[:3]:
            reporter.log(f"  - {error}", "WARNING")

    reporter.log(f"Correct Classifications:")
    reporter.log(f"  True Positives (caught invalid):  {results['true_positives']}")
    reporter.log(f"  True Negatives (passed valid):    {results['true_negatives']}")
    reporter.log(f"Errors:")
    reporter.log(f"  False Positives (blocked valid):  {results['false_positives']}")
    reporter.log(f"  False Negatives (missed invalid): {results['false_negatives']}")

    accuracy = (results['true_positives'] + results['true_negatives']) / total
    precision = results['true_positives'] / (results['true_positives'] + results['false_positives']) if (results['true_positives'] + results['false_positives']) > 0 else 0
    recall = results['true_positives'] / (results['true_positives'] + results['false_negatives']) if (results['true_positives'] + results['false_negatives']) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    reporter.log(f"Metrics:")
    reporter.log(f"  Accuracy:  {accuracy:.2%}")
    reporter.log(f"  Precision: {precision:.2%}")
    reporter.log(f"  Recall:    {recall:.2%}")
    reporter.log(f"  F1 Score:  {f1:.2%}")

    return {
        **results,
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'total_errors': results['false_positives'] + results['false_negatives']
    }


def run_optimization(args, reporter: OptimizationReporter):
    """Main optimization workflow."""

    # Load environment
    load_dotenv()

    # Load dataset
    df = load_dataset(Path(args.dataset), reporter)

    # Create DSPy examples
    training_examples = create_dspy_examples(df, reporter)

    # Define metrics
    accuracy_metric, security_metric, f1_metric = define_metrics(reporter)

    # Split dataset
    reporter.section("Splitting Dataset")
    train_set, val_set = train_test_split(
        training_examples,
        test_size=0.2,
        random_state=42,
        stratify=[ex.is_valid for ex in training_examples]
    )

    reporter.log(f"Training set: {len(train_set)} examples")
    reporter.log(f"Validation set: {len(val_set)} examples")
    reporter.log(f"Training - Valid: {sum(1 for ex in train_set if ex.is_valid)}, Invalid: {sum(1 for ex in train_set if not ex.is_valid)}")
    reporter.log(f"Validation - Valid: {sum(1 for ex in val_set if ex.is_valid)}, Invalid: {sum(1 for ex in val_set if not ex.is_valid)}")

    # Configure models
    reporter.section("Configuring Models")
    teacher_lm = dspy.LM('gemini/gemini-2.5-pro', api_key=os.getenv('GEMINI_API_KEY'), cache=False)
    student_lm = dspy.LM('gemini/gemini-2.5-flash-lite', api_key=os.getenv('GEMINI_API_KEY'), cache=False)

    reporter.log(f"Teacher Model: {teacher_lm.model}")
    reporter.log(f"Student Model: {student_lm.model}")

    dspy.configure(lm=student_lm)

    # Create guardrail module
    reporter.section("Creating Guardrail Module")
    guardrail_module = PreGuardrails()
    reporter.log("PreGuardrails module initialized")

    # Baseline evaluation
    reporter.section("Baseline Benchmark")
    reporter.log("Evaluating unoptimized model...")

    from dspy.evaluate import Evaluate

    evaluator = Evaluate(
        devset=val_set,
        metric=accuracy_metric,
        num_threads=1,
        display_progress=True,
        display_table=0
    )

    baseline_result = evaluator(guardrail_module)
    baseline_score = baseline_result['metric'] if isinstance(baseline_result, dict) else float(baseline_result)
    reporter.log(f"Baseline Accuracy: {baseline_score/100:.2%}")

    baseline_results = analyze_predictions(guardrail_module, val_set, reporter, "BASELINE")

    # Optimization
    reporter.section("BootstrapFewShot Optimization")
    reporter.log("Initializing optimizer...")

    from dspy.teleprompt import BootstrapFewShot

    optimizer = BootstrapFewShot(
        metric=security_metric,
        max_bootstrapped_demos=args.max_bootstrapped_demos,
        max_labeled_demos=args.max_labeled_demos,
        teacher_settings=dict(lm=teacher_lm)
    )

    reporter.log(f"Configuration:")
    reporter.log(f"  - Metric: security_focused_metric")
    reporter.log(f"  - Max bootstrapped demos: {args.max_bootstrapped_demos}")
    reporter.log(f"  - Max labeled demos: {args.max_labeled_demos}")
    reporter.log(f"  - Teacher LM: {teacher_lm.model}")

    reporter.log("Starting compilation (this may take several minutes)...")
    optimized_guardrail = optimizer.compile(
        student=guardrail_module,
        trainset=train_set
    )

    reporter.log("Optimization complete!")

    # Post-optimization evaluation
    reporter.section("Post-Optimization Benchmark")
    reporter.log("Evaluating optimized model...")

    optimized_result = evaluator(optimized_guardrail)
    optimized_score = optimized_result['metric'] if isinstance(optimized_result, dict) else float(optimized_result)
    reporter.log(f"Optimized Accuracy: {optimized_score/100:.2%}")

    optimized_results = analyze_predictions(optimized_guardrail, val_set, reporter, "OPTIMIZED")

    # Comparison
    reporter.section("Final Comparison")
    improvement = optimized_score - baseline_score
    reporter.log(f"Baseline:  {baseline_score/100:.2%}")
    reporter.log(f"Optimized: {optimized_score/100:.2%}")
    reporter.log(f"Improvement: {improvement/100:+.2%} ({improvement/baseline_score*100:+.1f}%)")

    error_reduction = baseline_results['total_errors'] - optimized_results['total_errors']
    error_reduction_pct = (error_reduction / baseline_results['total_errors'] * 100) if baseline_results['total_errors'] > 0 else 0
    reporter.log(f"Error Reduction: {error_reduction} ({error_reduction_pct:.1f}%)")

    # Multi-metric evaluation
    reporter.section("Multi-Metric Evaluation")

    multi_metric_results = {}

    for metric_name, metric_func in [
        ('Accuracy (Balanced)', accuracy_metric),
        ('Security-Focused', security_metric),
        ('F1-Balanced', f1_metric)
    ]:
        evaluator_temp = Evaluate(
            devset=val_set,
            metric=metric_func,
            num_threads=1,
            display_progress=False
        )

        baseline_temp = evaluator_temp(guardrail_module)
        optimized_temp = evaluator_temp(optimized_guardrail)

        baseline_val = baseline_temp['metric'] if isinstance(baseline_temp, dict) else float(baseline_temp)
        optimized_val = optimized_temp['metric'] if isinstance(optimized_temp, dict) else float(optimized_temp)
        improvement_val = optimized_val - baseline_val

        reporter.log(f"{metric_name}:")
        reporter.log(f"  Baseline:    {baseline_val/100:.2%}")
        reporter.log(f"  Optimized:   {optimized_val/100:.2%}")
        reporter.log(f"  Improvement: {improvement_val/100:+.2%}")

        multi_metric_results[metric_name] = {
            'baseline': baseline_val / 100,
            'optimized': optimized_val / 100,
            'improvement': improvement_val / 100
        }

    # Save optimized model with versioning
    reporter.section("Saving Optimized Model")

    version = args.version
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    output_dir = project_root / "src" / "app" / "optimized" / "PreGuardrails"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save versioned model
    versioned_path = output_dir / f"{version}_{timestamp}.json"
    optimized_guardrail.validator.save(str(versioned_path))
    reporter.log(f"Versioned model saved: {versioned_path}")

    # Copy/link as current
    current_path = output_dir / "current.json"
    if current_path.exists():
        # Backup previous current
        backup_path = output_dir / f"current_backup_{timestamp}.json"
        current_path.rename(backup_path)
        reporter.log(f"Previous model backed up: {backup_path}")

    # Copy versioned to current
    import shutil
    shutil.copy2(versioned_path, current_path)
    reporter.log(f"Current model updated: {current_path}")

    # Create metadata
    metadata = {
        'version': version,
        'timestamp': timestamp,
        'versioned_file': str(versioned_path.name),
        'dataset': str(args.dataset),
        'teacher_model': teacher_lm.model,
        'student_model': student_lm.model,
        'baseline_accuracy': baseline_score / 100,
        'optimized_accuracy': optimized_score / 100,
        'improvement': improvement / 100,
        'baseline_recall': baseline_results['recall'],
        'optimized_recall': optimized_results['recall']
    }

    metadata_path = output_dir / "current_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    reporter.log(f"Metadata saved: {metadata_path}")

    # Generate comprehensive report
    reporter.section("Generating Report")

    end_time = datetime.now()
    duration = end_time - reporter.start_time

    report_data = {
        'version': version,
        'timestamp': timestamp,
        'duration': str(duration),
        'config': {
            'dataset_path': str(args.dataset),
            'teacher_model': teacher_lm.model,
            'student_model': student_lm.model,
            'train_size': len(train_set),
            'val_size': len(val_set),
            'max_bootstrapped_demos': args.max_bootstrapped_demos,
            'max_labeled_demos': args.max_labeled_demos
        },
        'results': {
            'baseline': baseline_results,
            'optimized': optimized_results,
            'error_reduction_pct': error_reduction_pct,
            'multi_metric': multi_metric_results
        },
        'files': {
            'versioned_model': str(versioned_path),
            'current_model': str(current_path),
            'metadata': str(metadata_path)
        }
    }

    reports_dir = project_root / "reports" / "optimization"
    reporter.save_report(report_data, version)

    reporter.section("Optimization Complete")
    reporter.log(f"Total duration: {duration}")
    reporter.log(f"Optimized model: {current_path}")

    if optimized_results['recall'] >= 0.85:
        reporter.log("✅ APPROVED FOR PRODUCTION (Recall >= 85%)")
    elif optimized_results['recall'] >= 0.75:
        reporter.log("⚠️ REVIEW REQUIRED (Recall < 85%)", "WARNING")
    else:
        reporter.log("❌ NOT RECOMMENDED (Recall < 75%)", "ERROR")

    return report_data


def main():
    parser = argparse.ArgumentParser(
        description="Automated PreGuardrails Optimization with BootstrapFewShot"
    )
    parser.add_argument(
        '--dataset',
        type=str,
        required=True,
        help='Path to the dataset CSV file'
    )
    parser.add_argument(
        '--version',
        type=str,
        default=datetime.now().strftime("v%Y%m%d"),
        help='Version identifier for the optimized model (default: vYYYYMMDD)'
    )
    parser.add_argument(
        '--max-bootstrapped-demos',
        type=int,
        default=4,
        help='Maximum number of bootstrapped demonstrations (default: 4)'
    )
    parser.add_argument(
        '--max-labeled-demos',
        type=int,
        default=8,
        help='Maximum number of labeled demonstrations (default: 8)'
    )

    args = parser.parse_args()

    # Initialize reporter
    reports_dir = project_root / "reports" / "optimization"
    reporter = OptimizationReporter(reports_dir)

    reporter.section("PreGuardrails Optimization")
    reporter.log(f"Version: {args.version}")
    reporter.log(f"Dataset: {args.dataset}")
    reporter.log(f"Started at: {reporter.start_time}")

    try:
        report_data = run_optimization(args, reporter)
        reporter.log("Optimization completed successfully!")
        return 0

    except Exception as e:
        reporter.log(f"Optimization failed: {str(e)}", "ERROR")
        import traceback
        reporter.log(traceback.format_exc(), "ERROR")
        return 1


if __name__ == "__main__":
    sys.exit(main())
