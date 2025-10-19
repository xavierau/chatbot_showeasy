"""
Continuous Learning Pipeline for ConversationOrchestrator

This pipeline handles:
1. Collecting user conversations
2. Curating/canonicalizing data
3. Incremental retraining
4. A/B testing new models
5. Monitoring performance drift
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import pandas as pd
from curate_user_data import UserDataCurator, BehaviorOnlyTrainingSet


class ContinuousLearningPipeline:
    """Manages continuous learning from production data."""

    def __init__(self, config_path: str = "config/continuous_learning.json"):
        self.config = self._load_config(config_path)
        self.curator = UserDataCurator()

    def _load_config(self, path: str) -> Dict:
        """Load pipeline configuration."""
        default_config = {
            "collection": {
                "log_retention_days": 180,
                "min_quality_score": 0.7,
                "sample_rate": 1.0,  # Collect 100% of conversations
                "exclude_patterns": ["test_", "admin_"]
            },
            "curation": {
                "batch_size": 1000,
                "min_examples_for_retrain": 100,
                "max_age_days": 90
            },
            "retraining": {
                "frequency_days": 30,
                "validation_split": 0.2,
                "min_improvement_threshold": 0.02  # 2% improvement to deploy
            },
            "monitoring": {
                "performance_window_days": 7,
                "drift_threshold": 0.05  # 5% performance drop triggers alert
            }
        }

        if Path(path).exists():
            with open(path) as f:
                user_config = json.load(f)
                default_config.update(user_config)

        return default_config

    def collect_production_logs(
        self,
        start_date: datetime,
        end_date: datetime,
        output_path: str
    ) -> pd.DataFrame:
        """
        Collect conversation logs from production.

        In practice, this would query your production database/logs.
        """
        # Pseudo-code for production integration:
        """
        SELECT
            user_query,
            agent_response,
            tool_calls,
            quality_score,
            timestamp,
            page_context,
            user_id,
            session_id
        FROM conversation_logs
        WHERE timestamp BETWEEN start_date AND end_date
          AND quality_score >= min_quality_score
        """

        # For now, return placeholder
        print(f"📥 Collecting logs from {start_date} to {end_date}")
        return pd.DataFrame()

    def curate_batch(
        self,
        raw_logs_path: str,
        output_path: str
    ) -> Tuple[int, int]:
        """
        Curate a batch of raw logs into training data.

        Returns:
            (total_logs, valid_examples)
        """
        print(f"\n🔄 Curating logs from {raw_logs_path}")

        # Process logs
        curated = self.curator.process_user_logs(
            log_file=raw_logs_path,
            output_file=output_path,
            min_quality_score=self.config['collection']['min_quality_score']
        )

        return len(curated), sum(1 for item in curated if item['is_valid'])

    def create_incremental_training_set(
        self,
        existing_trainset_path: str,
        new_curated_path: str,
        output_path: str
    ) -> Dict:
        """
        Merge existing training data with new curated data.

        Strategy:
        1. Keep existing synthetic/hand-crafted examples (always valid)
        2. Add new canonicalized user examples
        3. Remove duplicates
        4. Balance across intents
        """
        print(f"\n🔗 Creating incremental training set")

        # Load existing
        with open(existing_trainset_path) as f:
            existing = json.load(f)

        # Load new curated
        with open(new_curated_path) as f:
            new_curated = json.load(f)

        # Convert to behavior-focused examples
        new_examples = BehaviorOnlyTrainingSet.create_from_curated_data(
            [item for item in new_curated if item['is_valid']]
        )

        # Merge
        all_examples = existing + new_examples

        # Deduplicate (by canonical query)
        seen = set()
        deduplicated = []
        for ex in all_examples:
            key = ex['user_input'].lower().strip()
            if key not in seen:
                seen.add(key)
                deduplicated.append(ex)

        # Balance across intents
        balanced = self._balance_intents(deduplicated)

        # Save
        with open(output_path, 'w') as f:
            json.dump(balanced, f, indent=2, ensure_ascii=False)

        stats = {
            'total_examples': len(balanced),
            'existing_kept': len([ex for ex in balanced if ex in existing]),
            'new_added': len([ex for ex in balanced if ex not in existing]),
            'duplicates_removed': len(all_examples) - len(deduplicated)
        }

        print(f"  Total: {stats['total_examples']}")
        print(f"  New: +{stats['new_added']}")
        print(f"  Duplicates removed: {stats['duplicates_removed']}")

        return stats

    def _balance_intents(self, examples: List[Dict]) -> List[Dict]:
        """Balance training set across intent categories."""
        # Group by intent
        by_intent = {}
        for ex in examples:
            intent = ex.get('intent_category', 'other')
            if intent not in by_intent:
                by_intent[intent] = []
            by_intent[intent].append(ex)

        # Find target size (mean)
        target_per_intent = max(
            len(by_intent.get('event_search', [])),
            len(by_intent.get('membership_inquiry', [])),
            50  # Minimum 50 per intent
        )

        balanced = []
        for intent, intent_examples in by_intent.items():
            if len(intent_examples) < target_per_intent:
                # Undersample: keep all
                balanced.extend(intent_examples)
            else:
                # Oversample: randomly sample to target
                import random
                random.seed(42)
                sampled = random.sample(intent_examples, target_per_intent)
                balanced.extend(sampled)

        return balanced

    def retrain_model(
        self,
        trainset_path: str,
        output_model_path: str,
        baseline_model_path: str = None
    ) -> Dict:
        """
        Retrain ConversationOrchestrator with new data.

        Returns metrics comparing to baseline.
        """
        print(f"\n🔄 Retraining model with {trainset_path}")

        # Load training data
        with open(trainset_path) as f:
            trainset = json.load(f)

        # Split train/val
        val_split = self.config['retraining']['validation_split']
        split_idx = int(len(trainset) * (1 - val_split))
        train_examples = trainset[:split_idx]
        val_examples = trainset[split_idx:]

        # TODO: Integrate with actual optimization code
        """
        from app.llm.modules import ConversationOrchestrator
        import dspy

        orchestrator = ConversationOrchestrator()

        # Stage 1: BootstrapFewShot
        bootstrap = BootstrapFewShot(...)
        stage1 = bootstrap.compile(orchestrator, trainset=train_examples)

        # Stage 2: GEPA
        gepa = dspy.GEPA(...)
        optimized = gepa.compile(stage1, trainset=train_examples, valset=val_examples)

        # Save
        optimized.save(output_model_path)
        """

        # For now, return placeholder metrics
        metrics = {
            'training_examples': len(train_examples),
            'validation_examples': len(val_examples),
            'baseline_score': 0.75,
            'new_model_score': 0.78,
            'improvement': 0.03,
            'trained_at': datetime.now().isoformat()
        }

        print(f"  Baseline: {metrics['baseline_score']:.2%}")
        print(f"  New model: {metrics['new_model_score']:.2%}")
        print(f"  Improvement: +{metrics['improvement']:.2%}")

        return metrics

    def should_deploy_new_model(self, metrics: Dict) -> Tuple[bool, str]:
        """Decide whether to deploy newly trained model."""
        threshold = self.config['retraining']['min_improvement_threshold']
        improvement = metrics.get('improvement', 0)

        if improvement >= threshold:
            return True, f"Improvement {improvement:.2%} exceeds threshold {threshold:.2%}"
        else:
            return False, f"Improvement {improvement:.2%} below threshold {threshold:.2%}"

    def monitor_performance_drift(
        self,
        model_version: str,
        window_days: int = 7
    ) -> Dict:
        """
        Monitor for performance degradation in production.

        Detects:
        - Accuracy drift
        - New user patterns
        - Changing data distribution
        """
        print(f"\n📊 Monitoring performance drift (last {window_days} days)")

        # In practice, query production metrics
        """
        SELECT
            DATE(timestamp) as date,
            AVG(user_satisfaction_score) as avg_score,
            COUNT(*) as conversation_count
        FROM conversation_logs
        WHERE model_version = :model_version
          AND timestamp >= NOW() - INTERVAL :window_days DAY
        GROUP BY DATE(timestamp)
        """

        # Placeholder metrics
        current_performance = 0.76
        baseline_performance = 0.78
        drift = baseline_performance - current_performance

        threshold = self.config['monitoring']['drift_threshold']

        result = {
            'model_version': model_version,
            'current_performance': current_performance,
            'baseline_performance': baseline_performance,
            'drift': drift,
            'threshold': threshold,
            'alert': drift > threshold,
            'checked_at': datetime.now().isoformat()
        }

        if result['alert']:
            print(f"  ⚠️ ALERT: Performance drift detected!")
            print(f"     Drift: {drift:.2%} (threshold: {threshold:.2%})")
        else:
            print(f"  ✓ Performance stable (drift: {drift:.2%})")

        return result

    def run_weekly_pipeline(self):
        """
        Run the complete weekly continuous learning pipeline.

        Steps:
        1. Collect last week's production logs
        2. Curate into training data
        3. Create incremental training set
        4. Retrain model
        5. Evaluate improvement
        6. Deploy if improvement exceeds threshold
        7. Monitor for drift
        """
        print("="*80)
        print("🚀 CONTINUOUS LEARNING PIPELINE")
        print("="*80)

        # 1. Collect logs
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        raw_logs = self.collect_production_logs(
            start_date=start_date,
            end_date=end_date,
            output_path='logs/weekly_raw.csv'
        )

        # 2. Curate
        total, valid = self.curate_batch(
            raw_logs_path='logs/weekly_raw.csv',
            output_path='datasets/weekly_curated.json'
        )

        # Check if enough new data
        min_examples = self.config['curation']['min_examples_for_retrain']
        if valid < min_examples:
            print(f"\n⏸️ Not enough new examples ({valid} < {min_examples})")
            print("   Skipping retraining this week")
            return

        # 3. Create incremental training set
        stats = self.create_incremental_training_set(
            existing_trainset_path='datasets/conversation_react_training.json',
            new_curated_path='datasets/weekly_curated.json',
            output_path='datasets/incremental_trainset.json'
        )

        # 4. Retrain
        metrics = self.retrain_model(
            trainset_path='datasets/incremental_trainset.json',
            output_model_path='models/candidate_model.json',
            baseline_model_path='models/production_model.json'
        )

        # 5. Decide deployment
        should_deploy, reason = self.should_deploy_new_model(metrics)

        print(f"\n🎯 Deployment Decision: {'✓ DEPLOY' if should_deploy else '✗ SKIP'}")
        print(f"   Reason: {reason}")

        if should_deploy:
            # In production, this would:
            # - Run A/B test
            # - Gradual rollout
            # - Monitor metrics
            print("   📦 Deploying new model to production...")

        # 6. Monitor drift
        drift_report = self.monitor_performance_drift(
            model_version='production_v1',
            window_days=7
        )

        print("\n" + "="*80)
        print("✅ PIPELINE COMPLETE")
        print("="*80)


# Example configuration file
EXAMPLE_CONFIG = {
    "collection": {
        "log_retention_days": 180,
        "min_quality_score": 0.7,
        "sample_rate": 1.0,
        "exclude_patterns": ["test_", "admin_"]
    },
    "curation": {
        "batch_size": 1000,
        "min_examples_for_retrain": 100,
        "max_age_days": 90
    },
    "retraining": {
        "frequency_days": 7,  # Weekly retraining
        "validation_split": 0.2,
        "min_improvement_threshold": 0.02
    },
    "monitoring": {
        "performance_window_days": 7,
        "drift_threshold": 0.05
    }
}


if __name__ == "__main__":
    # Run weekly pipeline
    pipeline = ContinuousLearningPipeline()
    pipeline.run_weekly_pipeline()
