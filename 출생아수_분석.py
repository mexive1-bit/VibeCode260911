"""1970~2024년 출생아수 데이터 정제 및 시각화."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


FILE_PATH = Path(__file__).with_name("출생아수__합계출산율__자연증가_등.xlsx")
OUTPUT_PATH = Path(__file__).with_name("출생아수_1970_2024.png")
START_YEAR = 1970
END_YEAR = 2024


def load_and_clean_data(file_path: Path) -> pd.DataFrame:
    """엑셀의 전치형 통계표를 연도별 데이터프레임으로 변환하고 정제한다."""
    raw = pd.read_excel(file_path, sheet_name="데이터", header=0)
    raw = raw.rename(columns={raw.columns[0]: "항목"})

    # 지표를 행에서 열로 바꾸고, 연도 열은 숫자로 변환한다.
    data = raw.set_index("항목").T.reset_index(names="연도")
    data["연도"] = pd.to_numeric(
        data["연도"].astype(str).str.extract(r"(\d{4})")[0], errors="coerce"
    )
    data["출생아수(명)"] = pd.to_numeric(
        data["출생아수(명)"].astype(str).str.replace(",", "", regex=False),
        errors="coerce",
    )

    # 분석 대상 기간만 남기고, 연도/출생아수가 없는 행과 중복 연도를 제거한다.
    data = data.loc[
        data["연도"].between(START_YEAR, END_YEAR)
        & data["출생아수(명)"].notna()
    ].copy()
    data = data.drop_duplicates(subset="연도").sort_values("연도")
    data["연도"] = data["연도"].astype(int)
    data["출생아수(명)"] = data["출생아수(명)"].astype(int)

    if data.empty:
        raise ValueError("1970~2024년 출생아수 데이터가 없습니다.")

    return data.reset_index(drop=True)


def analyze_births(data: pd.DataFrame) -> None:
    """정제 데이터의 기본 통계를 출력한다."""
    first = data.iloc[0]
    last = data.iloc[-1]
    highest = data.loc[data["출생아수(명)"].idxmax()]
    lowest = data.loc[data["출생아수(명)"].idxmin()]
    change_rate = (last["출생아수(명)"] / first["출생아수(명)"] - 1) * 100

    print(f"분석 기간: {data['연도'].min()}~{data['연도'].max()}년")
    print(f"분석 행 수: {len(data)}개")
    print(f"최다 출생아수: {int(highest['출생아수(명)']):,}명 ({int(highest['연도'])}년)")
    print(f"최소 출생아수: {int(lowest['출생아수(명)']):,}명 ({int(lowest['연도'])}년)")
    print(f"1970년 대비 2024년 증감률: {change_rate:.1f}%")
    print("\n기술통계:")
    print(data["출생아수(명)"].describe().round(0).to_string())


def plot_births(data: pd.DataFrame, output_path: Path) -> None:
    """연도별 출생아수 라인 그래프를 화면에 표시하고 PNG로 저장한다."""
    plt.rcParams["font.family"] = ["Malgun Gothic", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(
        data["연도"],
        data["출생아수(명)"],
        color="#1f77b4",
        linewidth=2,
        marker="o",
        markersize=3,
    )
    ax.set_title("1970~2024년 출생아수 추이", fontsize=16, pad=12)
    ax.set_xlabel("연도")
    ax.set_ylabel("출생아수(명)")
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.yaxis.set_major_formatter(lambda value, _: f"{value:,.0f}")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"그래프 저장: {output_path}")
    plt.show()


if __name__ == "__main__":
    cleaned_data = load_and_clean_data(FILE_PATH)
    analyze_births(cleaned_data)
    plot_births(cleaned_data, OUTPUT_PATH)