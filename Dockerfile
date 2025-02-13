FROM registry.access.redhat.com/ubi9/ubi-minimal
RUN microdnf install python3-requests -y && \
    microdnf clean all && \
    rm -rf /var/cache/yum
RUN mkdir /src
USER 1001
WORKDIR /src
COPY --chown=1001:1001 pac-boussole  .
COPY --chown=1001:1001 boussole /src/boussole
ENTRYPOINT ["python3", "/src/pac-boussole"]
