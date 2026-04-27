"""Deprecated pre-portfolio endpoints returning HTTP 410 Gone."""

from fastapi import APIRouter, HTTPException, status

router = APIRouter(tags=["deprecated"])

_DETAIL = (
    "This endpoint is deprecated. Use portfolio-scoped paths under "
    "/api/v1/portfolios/{portfolio_id}/..."
)


def _gone() -> None:
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=_DETAIL)


@router.api_route("/trades", methods=["GET", "POST"])
@router.post("/trades/bulk/delete")
@router.post("/trades/bulk/assign-tags")
@router.post("/trades/bulk/assign-playbook")
@router.post("/trades/merge")
@router.api_route("/trades/{trade_id}", methods=["GET", "PATCH", "DELETE"])
@router.post("/trades/{trade_id}/partial-close")
def deprecated_trades() -> None:
    _gone()


@router.get("/metrics/summary")
@router.get("/metrics/equity-curve")
@router.get("/metrics/drawdown")
def deprecated_metrics() -> None:
    _gone()


@router.get("/timeseries/daily-pnl")
@router.get("/timeseries/monthly-pnl")
@router.get("/timeseries/pnl-by-symbol")
@router.get("/timeseries/pnl-by-asset-class")
@router.get("/timeseries/return-distribution")
@router.get("/timeseries/rolling-winrate")
@router.get("/timeseries/monthly-winrate")
def deprecated_timeseries() -> None:
    _gone()


@router.post("/imports/upload")
@router.post("/imports/{account_id}/fresh-start")
@router.post("/imports/flex")
@router.post("/imports/schwab-json")
@router.patch("/imports/broker-raw-transactions/{raw_id}/suppress")
def deprecated_imports() -> None:
    _gone()


@router.api_route("/accounts", methods=["GET", "POST"])
@router.api_route("/accounts/{account_id}", methods=["GET", "PATCH", "DELETE"])
@router.get("/accounts/{account_id}/metrics")
def deprecated_accounts() -> None:
    _gone()


@router.get("/trades/{trade_id}/executions")
@router.post("/trades/{trade_id}/executions")
@router.patch("/executions/{execution_id}")
@router.delete("/executions/{execution_id}")
@router.post("/executions/{execution_id}/restore")
@router.post("/executions/{execution_id}/split")
@router.post("/executions/merge")
@router.post("/executions/{execution_id}/reassign")
@router.post("/executions/{execution_id}/detach")
def deprecated_executions() -> None:
    _gone()


@router.api_route(
    "/accounts/{account_id}/cash-transactions",
    methods=["GET", "POST"],
)
@router.api_route(
    "/accounts/{account_id}/cash-transactions/{transaction_id}",
    methods=["GET", "PATCH", "DELETE"],
)
def deprecated_cash_transactions() -> None:
    _gone()
