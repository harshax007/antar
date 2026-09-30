"""
Tests for Alert Suggest Agent
"""
import pytest
from app.agents.alert_suggest_agent import alert_suggest_agent_run

@pytest.mark.anyio
async def test_alert_suggest_agent_run():
    # Calling the agent run
    res = await alert_suggest_agent_run("what are the deployment suggestions", {})
    assert "alerts" in res
    assert "summary" in res
