FROM python:3.13.4-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /var/app

RUN pip install --upgrade pip "uv==0.6.3"

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

ENV PATH="/var/app/.venv/bin:$PATH"

COPY . .

CMD ["gunicorn", "django_blog.wsgi:application", "-b", "0.0.0.0:8000"]



