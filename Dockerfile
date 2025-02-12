FROM registry.access.redhat.com/ubi9/ubi-minimal
RUN microdnf install python3-requests -y && \
    microdnf clean all && \
    rm -rf /var/cache/yum
RUN mkdir /src
USER 1001
COPY --chown=1001:1001 pipelines-as-code-prow  /src
COPY --chown=1001:1001 pipelines_as_code_prow /src/pipelines_as_code_prow
ENTRYPOINT ["python3", "/src/pipelines-as-code-prow"]
