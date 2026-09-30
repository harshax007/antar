from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api import pattern_predict
import pytest

app = FastAPI()
app.include_router(pattern_predict.router, prefix="/api")

client = TestClient(app)

def test_predict_endpoint_returns_structured_trace():
    response = client.get("/api/predict?zone=Rajajinagar&crime_type=theft")
    assert response.status_code == 200
    data = response.json()
    
    assert "risk" in data
    assert "confidence" in data
    assert "drivers" in data
    assert "trace" in data
    
    # Assert drivers are weighted dicts
    assert len(data["drivers"]) > 0
    assert "factor" in data["drivers"][0]
    assert "weight" in data["drivers"][0]
    
    # Assert traces are structured dicts with >=3 steps
    assert len(data["trace"]) >= 3
    for step in data["trace"]:
        assert "step" in step
        assert "description" in step
        assert "data_refs" in step
        assert isinstance(step["data_refs"], list)

def test_predict_model_card_endpoint():
    response = client.get("/api/predict/model-card")
    assert response.status_code == 200
    data = response.json()
    
    # Generated from what runs (app/forecast/card.py) — no longer the hand-written card
    # that described DBSCAN and claimed a live CCTNS replica.
    assert data["model_name"].startswith("Antar Map Forecast")
    assert data["generated"] is True and data["evidence_class"] == "I"
    assert "DBSCAN" not in data["architecture"]
    assert "CCTNS live replica" not in data["data_provenance"]
    assert "bias_disclosure" in data
    assert len(data["bias_disclosure"]) >= 2
    assert "false_positive_mitigation" in data
    assert data["evaluation"]
