FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential tree curl git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /src

RUN pip install jupyter==1.0.0 poetry==1.8.3 && curl -s https://pyenv.run | bash

CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--NotebookApp.token=''"]