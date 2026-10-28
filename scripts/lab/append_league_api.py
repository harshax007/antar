from pathlib import Path

path = Path("app/api/forecast_api.py")
code_to_add = '''


@router.get("/league")
async def model_league() -> dict:
    """Champion vs Challenger model league table."""
    def work(con):
        from app.forecast import league as L
        table = L.load(con)
        if not table:
            bt = BT.load(con)
            if bt:
                table = L.build(bt, con)
                L.save(con, table)
            else:
                raise S.NotReady("League table unavailable — run: python -m app.forecast.backtest --challengers lgbm")
        return table
    return await _call(work)


@router.get("/league/explain")
async def model_league_explain(
    unit: str,
    category: str = "ALL",
    horizon: int = 7,
    as_of: Optional[str] = None,
) -> dict:
    """Driver breakdown for one unit side by side across champion GLM and challenger LightGBM."""
    def work(con):
        from app.forecast import features as F
        from app.forecast import model as M
        from app.forecast import challenger as C
        from app.forecast import asof as A
        
        a = A.resolve(con, as_of)
        ut = "beat" if "|" in unit else "station"
        st = F.load_units(con, "station")
        units = F.load_units(con, ut)
        cal = F.calendar(con, "n_real", a.history_end)
        pan = F.load_panel(con, units, st if ut == "beat" else None, category, cal)
        
        idx = units.index.get(unit)
        if idx is None:
            raise HTTPException(status_code=404, detail=f"Unit not found: {unit}")
            
        t = pan.week_index(a.as_of)
        
        # GLM Fit & explain
        fs = M.fit(pan, t - 1, horizon)
        parent = M.Parent(pan, fs) if ut == "beat" else None
        pred_glm = M.predict(pan, fs, t, parent=parent, explain=True)
        
        drivers_glm = {
            k: float(pred_glm[k][idx]) for k in pred_glm if k.startswith("x_")
        }
        
        # Challenger Fit & explain
        drivers_lgb = {}
        pred_lgb = {}
        try:
            c_fs = C.fit(pan, t - 1, horizon)
            pred_lgb = C.predict(pan, c_fs, t, parent=parent, explain=True)
            drivers_lgb = {
                k: float(pred_lgb[k][idx]) for k in pred_lgb if k.startswith("x_")
            }
        except Exception:
            pass
            
        return {
            "unit": unit,
            "unit_type": ut,
            "category": category,
            "horizon_days": horizon,
            "as_of": a.as_of.isoformat(),
            "glm": {
                "expected": float(pred_glm["expected"][idx]),
                "lo90": float(pred_glm["lo90"][idx]),
                "hi90": float(pred_glm["hi90"][idx]),
                "drivers": drivers_glm,
            },
            "lgbm": {
                "expected": float(pred_lgb["expected"][idx]) if "expected" in pred_lgb else None,
                "lo90": float(pred_lgb["lo90"][idx]) if "lo90" in pred_lgb else None,
                "hi90": float(pred_lgb["hi90"][idx]) if "hi90" in pred_lgb else None,
                "drivers": drivers_lgb,
            },
        }
    return await _call(work)
'''

content = path.read_text(encoding="utf-8")
if "/league" not in content:
    with open(path, "a", encoding="utf-8", newline="\r\n") as f:
        f.write(code_to_add)
    print("Added league endpoints to app/api/forecast_api.py")
else:
    print("Already present")
