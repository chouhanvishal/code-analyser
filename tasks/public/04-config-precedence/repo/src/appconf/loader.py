def load(defaults, file_values, env):
    result = {}
    result.update(env)
    result.update(file_values)
    result.update(defaults)
    return result
