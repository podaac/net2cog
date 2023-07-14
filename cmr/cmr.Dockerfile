FROM python:3.7-slim

## Create a new user
RUN adduser --quiet --disabled-password --shell /bin/sh --home /home/dockeruser --gecos "" --uid 300 dockeruser
USER dockeruser
ENV HOME /home/dockeruser
ENV PYTHONPATH "${PYTHONPATH}:/home/dockeruser/.local/bin"
ENV PATH="/home/dockeruser/.local/bin:${PATH}"

# Add artifactory as a trusted pip index
RUN mkdir $HOME/.pip && \
    echo "[global]" >> $HOME/.pip/pip.conf && \
    echo "index-url = https://cae-artifactory.jpl.nasa.gov/artifactory/api/pypi/pypi-release-virtual/simple" >> $HOME/.pip/pip.conf && \
    echo "trusted-host = cae-artifactory.jpl.nasa.gov podaac-ci.jpl.nasa.gov pypi.org"  >> $HOME/.pip/pip.conf && \
    echo "extra-index-url = https://podaac-ci.jpl.nasa.gov:8443/artifactory/api/pypi/pypi/simple https://pypi.org/simple" >> $HOME/.pip/pip.conf

WORKDIR "/home/dockeruser"

RUN pip install --upgrade pip \
    && pip install awscli --upgrade \
    && pip install podaac-dev-tools==0.2.0

RUN pip list
CMD ["sh"]