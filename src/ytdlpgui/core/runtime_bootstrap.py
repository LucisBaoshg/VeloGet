def runtime_setup_required(deps) -> bool:
    return bool(deps.get_missing_runtime_components())
