from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
from plotly.subplots import make_subplots


def build_candlestick_figure(
    candles: list[dict[str, Any]],
    indicators: dict[str, list[float | None]] | None = None,
    patterns: list[dict[str, Any]] | None = None,
) -> go.Figure:
    if not candles:
        fig = go.Figure()
        fig.update_layout(template="plotly_dark", height=520)
        return fig
    x = [c["ts"] for c in candles]
    o = [c["open"] for c in candles]
    h = [c["high"] for c in candles]
    l = [c["low"] for c in candles]
    cl = [c["close"] for c in candles]
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.55, 0.22, 0.23],
    )
    fig.add_trace(
        go.Candlestick(
            x=x,
            open=o,
            high=h,
            low=l,
            close=cl,
            name="Price",
            increasing_line_color="#34d399",
            decreasing_line_color="#f87171",
        ),
        row=1,
        col=1,
    )
    if indicators:
        vwap = indicators.get("vwap")
        if vwap and len(vwap) == len(candles):
            fig.add_trace(
                go.Scatter(x=x, y=vwap, name="VWAP", line=dict(color="#38bdf8", width=1.2)),
                row=1,
                col=1,
            )
        ten = indicators.get("ichimoku_tenkan")
        kij = indicators.get("ichimoku_kijun")
        if ten and len(ten) == len(candles):
            fig.add_trace(
                go.Scatter(x=x, y=ten, name="Tenkan", line=dict(color="#fbbf24", width=1)),
                row=1,
                col=1,
            )
        if kij and len(kij) == len(candles):
            fig.add_trace(
                go.Scatter(x=x, y=kij, name="Kijun", line=dict(color="#a78bfa", width=1)),
                row=1,
                col=1,
            )
        rsi = indicators.get("rsi14")
        if rsi and len(rsi) == len(candles):
            fig.add_trace(
                go.Scatter(x=x, y=rsi, name="RSI(14)", line=dict(color="#22d3ee", width=1.2)),
                row=2,
                col=1,
            )
            fig.add_hline(y=70, line_dash="dot", line_color="rgba(248,113,113,0.5)", row=2, col=1)
            fig.add_hline(y=30, line_dash="dot", line_color="rgba(52,211,153,0.5)", row=2, col=1)
        macd_line = indicators.get("macd")
        macd_sig = indicators.get("macd_signal")
        macd_hist = indicators.get("histogram") or indicators.get("macd_histogram")
        if not macd_hist and macd_line and macd_sig and len(macd_line) == len(candles):
            macd_hist = [
                (float(a) - float(b)) if a is not None and b is not None else None
                for a, b in zip(macd_line, macd_sig, strict=False)
            ]
        if macd_line and len(macd_line) == len(candles):
            fig.add_trace(
                go.Scatter(x=x, y=macd_line, name="MACD", line=dict(color="#f97316", width=1.1)),
                row=3,
                col=1,
            )
        if macd_sig and len(macd_sig) == len(candles):
            fig.add_trace(
                go.Scatter(x=x, y=macd_sig, name="Signal", line=dict(color="#60a5fa", width=1.0)),
                row=3,
                col=1,
            )
        if macd_hist and len(macd_hist) == len(candles):
            colors = ["#34d399" if (v or 0) >= 0 else "#f87171" for v in macd_hist]
            fig.add_trace(
                go.Bar(x=x, y=macd_hist, name="MACD hist", marker_color=colors, opacity=0.35),
                row=3,
                col=1,
            )
    if patterns:
        for p in patterns:
            name = p.get("name", "")
            s = int(p.get("start_index", 0))
            e = int(p.get("end_index", len(candles) - 1))
            if 0 <= s < len(candles) and 0 <= e < len(candles):
                x0 = candles[s]["ts"]
                x1 = candles[e]["ts"]
                y0 = min(candles[s]["low"], candles[e]["low"]) * 0.995
                y1 = max(candles[s]["high"], candles[e]["high"]) * 1.005
                fig.add_shape(
                    type="rect",
                    x0=x0,
                    x1=x1,
                    y0=y0,
                    y1=y1,
                    line=dict(color="#f472b6", width=1, dash="dash"),
                    fillcolor="rgba(244,114,182,0.08)",
                    row=1,
                    col=1,
                )
                fig.add_annotation(
                    x=x1,
                    y=y1,
                    text=name.replace("_", " ").title(),
                    showarrow=False,
                    font=dict(color="#fda4af", size=11),
                    row=1,
                    col=1,
                )
    fig.update_layout(
        template="plotly_dark",
        height=780,
        margin=dict(l=40, r=20, t=30, b=40),
        xaxis_rangeslider_visible=False,
        legend_orientation="h",
        barmode="overlay",
    )
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="RSI", row=2, col=1)
    fig.update_yaxes(title_text="MACD", row=3, col=1)
    return fig
