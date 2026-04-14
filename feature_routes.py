# api/routes/feature_routes.py
# The main POST endpoint: trigger a vehicle feature.

from fastapi import APIRouter, HTTPException, Request, Depends, status
from models.feature import FeatureRequest, FeatureResponse
from core.feature_dispatcher import FeatureDispatcher

router = APIRouter(prefix="/feature", tags=["Vehicle Features"])


def get_dispatcher(request: Request) -> FeatureDispatcher:
    return request.app.state.dispatcher


@router.post("/{feature_name}", response_model=FeatureResponse)
async def trigger_feature(
    feature_name: str,
    request_body: FeatureRequest,
    dispatcher: FeatureDispatcher = Depends(get_dispatcher),
) -> FeatureResponse:
    if request_body.feature_name != feature_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"URL feature '{feature_name}' does not match body feature '{request_body.feature_name}'.",
        )

    response = dispatcher.dispatch(feature_name=feature_name, requested_value=request_body.value)

    if not response.success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=response.message)

    return response


@router.get("/")
async def list_features(dispatcher: FeatureDispatcher = Depends(get_dispatcher)):
    return {"total": len(dispatcher.list_features()), "features": dispatcher.list_features()}