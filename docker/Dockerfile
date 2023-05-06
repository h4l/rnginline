ARG python_version
ARG python_user_uid
FROM python:${python_version:?}
ARG python_user_uid
RUN pip install poetry \
    && useradd python --uid "${python_user_uid:-1000}"
