from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


START_DATE = "2000-01-01"
END_DATE = "2019-12-31"
INPUT_FILE = Path(__file__).with_name("S&P 500 과거 데이터.csv")
OUTPUT_DIR = Path(__file__).with_name("sp500_analysis_output")


def clean_data(file_path: Path) -> pd.DataFrame:
    data = pd.read_csv(file_path, encoding="utf-8-sig")
    data.columns = data.columns.str.strip()

    data["날짜"] = pd.to_datetime(
        data["날짜"].astype("string").str.replace(r"\s+", "", regex=True),
        format="%Y-%m-%d",
        errors="coerce",
    )

    numeric_columns = ["종가", "시가", "고가", "저가", "거래량", "변동 %"]
    for column in numeric_columns:
        if column in data:
            data[column] = pd.to_numeric(
                data[column]
                .astype("string")
                .str.replace(",", "", regex=False)
                .str.replace("%", "", regex=False)
                .replace({"": pd.NA, "<NA>": pd.NA}),
                errors="coerce",
            )

    data = (
        data.dropna(subset=["날짜", "종가"])
        .drop_duplicates(subset=["날짜"])
        .sort_values("날짜")
        .set_index("날짜")
    )
    return data.loc[START_DATE:END_DATE].copy()


def make_analysis(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    data["일간 수익률"] = data["종가"].pct_change()
    data["누적 수익률"] = (1 + data["일간 수익률"].fillna(0)).cumprod() - 1
    data["고점 대비 하락률"] = data["종가"] / data["종가"].cummax() - 1
    data["20일 변동성"] = data["일간 수익률"].rolling(20).std() * np.sqrt(252)

    annual = data["종가"].resample("YE").agg(["first", "last", "min", "max"])
    annual["수익률"] = annual["last"].pct_change()
    annual["연중 변동폭"] = annual["max"] / annual["min"] - 1
    annual.index = annual.index.year

    monthly_returns = data["종가"].resample("ME").last().pct_change()
    monthly_returns = monthly_returns.to_frame("월간 수익률")
    monthly_returns["연도"] = monthly_returns.index.year
    monthly_returns["월"] = monthly_returns.index.month
    monthly_pivot = monthly_returns.pivot(index="연도", columns="월", values="월간 수익률")

    return data, annual, monthly_pivot


def print_summary(data: pd.DataFrame, annual: pd.DataFrame, monthly_pivot: pd.DataFrame) -> None:
    start_price = data["종가"].iloc[0]
    end_price = data["종가"].iloc[-1]
    total_return = end_price / start_price - 1
    years = (data.index[-1] - data.index[0]).days / 365.25
    cagr = (end_price / start_price) ** (1 / years) - 1
    max_drawdown = data["고점 대비 하락률"].min()
    annualized_volatility = data["일간 수익률"].std() * np.sqrt(252)

    print("[기간 및 정제 결과]")
    print(f"관측 기간: {data.index.min():%Y-%m-%d} ~ {data.index.max():%Y-%m-%d}")
    print(f"관측치: {len(data):,}개")
    core_columns = ["종가", "시가", "고가", "저가"]
    print(f"핵심 가격 컬럼 결측치: {data[core_columns].isna().sum().sum():,}개")
    print(f"종가: {start_price:,.2f} -> {end_price:,.2f}")
    print(f"누적 수익률: {total_return:.2%}")
    print(f"연복리 수익률(CAGR): {cagr:.2%}")
    print(f"연환산 변동성: {annualized_volatility:.2%}")
    print(f"최대 낙폭(MDD): {max_drawdown:.2%}")
    print(f"상승한 연도: {(annual['수익률'] > 0).sum()}개 / {annual['수익률'].notna().sum()}개")
    print("\n[연도별 요약]")
    annual_display = annual.copy()
    for column in ["first", "last", "min", "max"]:
        annual_display[column] = annual_display[column].map(lambda value: f"{value:,.2f}")
    for column in ["수익률", "연중 변동폭"]:
        annual_display[column] = annual_display[column].map(
            lambda value: "-" if pd.isna(value) else f"{value:.2%}"
        )
    print(annual_display.to_string())
    print("\n[월별 수익률 평균]")
    print(monthly_pivot.mean().to_string(float_format=lambda value: f"{value:.2%}"))


def save_outputs(data: pd.DataFrame, annual: pd.DataFrame, monthly_pivot: pd.DataFrame) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    data.to_csv(OUTPUT_DIR / "sp500_cleaned_daily.csv", encoding="utf-8-sig")
    annual.to_csv(OUTPUT_DIR / "sp500_annual_summary.csv", encoding="utf-8-sig")
    monthly_pivot.to_csv(OUTPUT_DIR / "sp500_monthly_returns.csv", encoding="utf-8-sig")


def plot_results(data: pd.DataFrame) -> None:
    plt.rcParams["font.family"] = ["Malgun Gothic", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    figure, axes = plt.subplots(3, 1, figsize=(15, 13), sharex=True)
    figure.suptitle("S&P 500 분석: 2000년 초 ~ 2019년 말", fontsize=18, fontweight="bold")

    axes[0].plot(data.index, data["종가"], color="#174a5b", linewidth=1.1)
    axes[0].set_title("종가 추이")
    axes[0].set_ylabel("지수")
    axes[0].grid(alpha=0.25)

    axes[1].plot(data.index, data["누적 수익률"] * 100, color="#b45f06", linewidth=1.1)
    axes[1].axhline(0, color="black", linewidth=0.7)
    axes[1].set_title("누적 수익률")
    axes[1].set_ylabel("수익률 (%)")
    axes[1].grid(alpha=0.25)

    axes[2].fill_between(
        data.index,
        data["고점 대비 하락률"] * 100,
        0,
        color="#a61c00",
        alpha=0.35,
    )
    axes[2].set_title("고점 대비 하락률")
    axes[2].set_ylabel("하락률 (%)")
    axes[2].grid(alpha=0.25)

    figure.tight_layout()
    figure.savefig(OUTPUT_DIR / "sp500_analysis_chart.png", dpi=160, bbox_inches="tight")
    plt.show()


def main() -> None:
    data = clean_data(INPUT_FILE)
    if data.empty:
        raise ValueError("지정한 기간에 사용할 수 있는 데이터가 없습니다.")

    data, annual, monthly_pivot = make_analysis(data)
    print_summary(data, annual, monthly_pivot)
    save_outputs(data, annual, monthly_pivot)
    plot_results(data)
    print(f"\n결과 저장 위치: {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()