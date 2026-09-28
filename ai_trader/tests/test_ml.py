from backend.ml.inference.predictor import Predictor
from backend.ml.models.registry.model_registry import ModelRegistry
from backend.ml.training.feature_builder import FeatureBuilder
from backend.ml.training.label_builder import LOSS, WIN, LabelBuilder
from backend.ml.training.srm_trainer import SRMTrainer


def _win(**extra):
    row = {
        "price": 1.0,
        "exit_price": 1.3,
        "liquidity": 80_000,
        "holder_count": 500,
        "volume": 40_000,
        "buys": 80,
        "sells": 30,
        "price_change_percent": 20,
        "is_honeypot": 0,
        "renounced": 1,
    }
    row.update(extra)
    return row


def _loss(**extra):
    row = {
        "price": 1.0,
        "exit_price": 0.7,
        "liquidity": 500,
        "holder_count": 8,
        "volume": 100,
        "buys": 2,
        "sells": 20,
        "price_change_percent": -30,
        "is_honeypot": 1,
        "renounced": 0,
    }
    row.update(extra)
    return row


def test_feature_and_label_builders():
    frame = FeatureBuilder().frame([_win(), _loss()])
    assert list(frame.columns) == FeatureBuilder.columns
    labels = LabelBuilder(horizon_return=0.1).from_records([_win(), _loss()])
    assert list(labels) == [WIN, LOSS]


def test_train_predict_roundtrip(tmp_path):
    records = [_win() for _ in range(8)] + [_loss() for _ in range(8)]
    trainer = SRMTrainer(registry=ModelRegistry(tmp_path), epochs=250, lr=0.2)
    model = trainer.fit(records, name="srm-test")
    predictor = Predictor(model=model, registry=ModelRegistry(tmp_path))
    assert predictor.probability(_win()) > predictor.probability(_loss())
    assert predictor.recommend(_win()) in {"BUY", "WATCH"}
    assert predictor.recommend(_loss()) in {"WATCH", "REJECT"}
    loaded = Predictor(registry=ModelRegistry(tmp_path))
    assert loaded.model is not None
