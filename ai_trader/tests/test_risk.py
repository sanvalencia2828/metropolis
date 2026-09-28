from backend.risk import DrawdownGuard, ExposureManager, KillSwitch, PositionSizer, RiskManager


def test_position_sizer_uses_fixed_risk_budget():
    size = PositionSizer().size(account_equity=1_000.0, entry_price=100.0, stop_loss_price=95.0)
    assert size == 2.0

    capped = PositionSizer(max_position_value=150.0).size(
        account_equity=1_000.0,
        entry_price=100.0,
        stop_loss_price=95.0,
    )
    assert capped == 1.5


def test_drawdown_guard_tracks_peak_to_trough():
    guard = DrawdownGuard(max_drawdown=0.10)
    assert guard.update(100.0) == 0.0
    assert not guard.triggered
    assert guard.update(89.0) == 0.11
    assert guard.triggered


def test_exposure_manager_caps_total_exposure():
    manager = ExposureManager(max_total_exposure=0.50)
    assert manager.add_exposure(0.20)
    assert not manager.add_exposure(0.40)
    assert manager.available_capacity() == 0.30


def test_kill_switch_and_risk_manager_block_risky_activity():
    switch = KillSwitch()
    assert not switch.active
    switch.trigger("abort")
    assert switch.active
    switch.reset()

    risk = RiskManager(max_daily_drawdown=0.15, max_portfolio_exposure=0.40)
    ok = risk.evaluate(100.0, new_exposure=0.10)
    assert ok.allowed

    blocked = risk.evaluate(80.0, new_exposure=0.10)
    assert not blocked.allowed
    assert risk.kill_switch.active
