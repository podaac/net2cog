FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    python3 \
    python3-dev \
    gcc \
    libssl-dev \
    libjpeg-dev \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libxslt1-dev \
    libnetcdf-dev \
    libhdf5-dev \
    hdf5-helpers \
    && pip3 install --upgrade pip \
    && apt-get clean

# Create a new user
RUN adduser --quiet --disabled-password --shell /bin/sh --home /home/dockeruser --gecos "" --uid 1000 dockeruser
USER dockeruser
ENV HOME /home/dockeruser
ENV PYTHONPATH "${PYTHONPATH}:/home/dockeruser/.local/bin"
ENV PATH="/home/dockeruser/.local/bin:${PATH}"

# Add artifactory as a trusted pip index
RUN mkdir $HOME/.pip
RUN echo "[global]" >> $HOME/.pip/pip.conf && \
    echo "index-url = https://cae-artifactory.jpl.nasa.gov/artifactory/api/pypi/pypi-release-virtual/simple" >> $HOME/.pip/pip.conf && \
    echo "trusted-host = cae-artifactory.jpl.nasa.gov maven.earthdata.nasa.gov pypi.org"  >> $HOME/.pip/pip.conf && \
    echo "extra-index-url = https://maven.earthdata.nasa.gov/repository/python-repo/simple https://pypi.org/simple" >> $HOME/.pip/pip.conf

# The 'SOURCE' argument is what will be used in 'pip install'.
ARG SOURCE

# Set this argument if running the pip install on a local directory, so
# the local dist files are copied into the container.
ARG DIST_PATH

USER root
RUN mkdir -p /worker && chown dockeruser /worker
USER dockeruser
WORKDIR /worker

COPY --chown=dockeruser $DIST_PATH $DIST_PATH
USER dockeruser
RUN pip3 install --use-feature=no-binary-enable-wheel-cache --force $SOURCE --user \
    && rm -rf $DIST_PATH

# Patch for rioxarray_raster
COPY ../net2cog/rioxarray_raster_patch.diff /home/dockeruser/.local/lib/python3.9/site-packages/rioxarray/raster_writer.py

# Run the subsetter
#ENTRYPOINT ["netcdf_harmony"]
CMD ["bash"]
