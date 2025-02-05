FROM registry.access.redhat.com/ubi9/ubi-minimal

RUN microdnf install python3-requests -y && \
    microdnf clean all && \
    rm -rf /var/cache/yum

ADD ./prow/prow.py /prow.py

ENTRYPOINT ["python3", "/prow.py"]
