#
# Test image for the Harmony ghcr.io/podaac/net2cog service. This
# image uses the main service image, ghcr.io/podaac/net2cog, as a base layer
# for the tests. This ensures  that the contents of the service image are
# tested, preventing discrepancies between the service and test environments.
#

ARG IMAGE_TAG
FROM ghcr.io/podaac/net2cog:$IMAGE_TAG

ENV DOCKER_RUNNING=1

WORKDIR /home
USER root

# Copy the necessary files to the Docker container for testing
COPY ./pyproject.toml pyproject.toml
COPY ./poetry.lock poetry.lock
COPY ./README.md README.md
COPY ./net2cog net2cog
COPY ./run_tests.sh run_tests.sh
COPY ./tests tests

# Install poetry
RUN python3 -m pip install poetry

# Running in Docker container, skipping virtualenv creation
RUN poetry config virtualenvs.create false

# Install [tool.poetry.group.dev.dependencies] and [tool.poetry.extras] 
# dependencies
RUN poetry install --no-root --with dev --all-extras

# Configure a container to be executable via the `docker run` command.
ENTRYPOINT ["/home/run_tests.sh"]