from fastapi import APIRouter, Header, HTTPException

from server.config import settings
from server.services.analysis import find_csv_files, load_session_data
from server.services.markdown import dataframe_to_markdown

router = APIRouter()


@router.get("/export/{group_id}")
async def export_group(
    group_id: str,
    x_engine_secret: str = Header(alias="X-Engine-Secret"),
):
    """그룹의 CSV 데이터를 Markdown으로 내보내는 엔드포인트임"""
    # secret_key 검증 수행함
    if x_engine_secret != settings.engine_secret_key:
        raise HTTPException(
            status_code=403, detail="인증 실패: 유효하지 않은 시크릿 키임"
        )

    dataframes = {}
    for idx in [1, 2]:
        csv_files = find_csv_files(group_id, idx)
        if csv_files:
            dataframes[idx] = load_session_data(csv_files[0])

    if not dataframes:
        raise HTTPException(
            status_code=404, detail=f"그룹 {group_id}의 CSV 파일 미발견"
        )

    markdown = dataframe_to_markdown(dataframes)
    return {"group_id": group_id, "markdown": markdown}
