from protocol.api._services import models_service


async def test_sanity():
    models = await models_service.list_models()
    mcp_model = await models_service.list_models_mcp()
    assert len(models) == len(mcp_model)


class TestListModelsMCP:
    async def test_default_does_not_include_icon_url(self):
        models = await models_service.list_models_mcp()
        assert all("icon_url" not in model for model in models)
