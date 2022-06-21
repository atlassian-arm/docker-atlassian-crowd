ARG BASE_IMAGE=eclipse-temurin:11
FROM $BASE_IMAGE

LABEL maintainer="dc-deployments@atlassian.com"
LABEL securitytxt="https://www.atlassian.com/.well-known/security.txt"

ENV APP_NAME                                        crowd
ENV RUN_USER                                        crowd
ENV RUN_GROUP                                       crowd
ENV RUN_UID                                         2004
ENV RUN_GID                                         2004

# https://confluence.atlassian.com/crowd/important-directories-and-files-78676537.html
ENV CROWD_HOME                                      /var/atlassian/application-data/crowd
ENV CROWD_INSTALL_DIR                               /opt/atlassian/crowd

WORKDIR $CROWD_HOME

# Expose HTTP port
EXPOSE 8095

CMD ["/entrypoint.py"]
ENTRYPOINT ["/usr/bin/tini", "--"]

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends fontconfig python3 python3-jinja2 tini \
    && apt-get clean autoclean && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

ARG CROWD_VERSION
ARG DOWNLOAD_URL=https://product-downloads.atlassian.com/software/crowd/downloads/atlassian-crowd-${CROWD_VERSION}.tar.gz

RUN groupadd --gid ${RUN_GID} ${RUN_GROUP} \
    && useradd --uid ${RUN_UID} --gid ${RUN_GID} --home-dir ${CROWD_HOME} ${RUN_USER} \
    \
    && mkdir -p                                     ${CROWD_INSTALL_DIR}/database \
    && curl -L --silent                             ${DOWNLOAD_URL} | tar -xz --strip-components=1 -C "${CROWD_INSTALL_DIR}" \
    && chmod -R "u=rwX,g=rX,o=rX"                   ${CROWD_INSTALL_DIR}/ \
    && chown -R root.                               ${CROWD_INSTALL_DIR}/ \
    && chown -R ${RUN_USER}:${RUN_GROUP}            ${CROWD_INSTALL_DIR}/apache-tomcat/logs \
    && chown -R ${RUN_USER}:${RUN_GROUP}            ${CROWD_INSTALL_DIR}/apache-tomcat/temp \
    && chown -R ${RUN_USER}:${RUN_GROUP}            ${CROWD_INSTALL_DIR}/apache-tomcat/work \
    && chown -R ${RUN_USER}:${RUN_GROUP}            ${CROWD_INSTALL_DIR}/database \
    && chown -R ${RUN_USER}:${RUN_GROUP}            ${CROWD_HOME} \
    \
    && sed -i -e 's/-Xms\([0-9]\+[kmg]\) -Xmx\([0-9]\+[kmg]\)/-Xms\${JVM_MINIMUM_MEMORY:=\1} -Xmx\${JVM_MAXIMUM_MEMORY:=\2} \${JVM_SUPPORT_RECOMMENDED_ARGS} -Dcrowd.home=\${CROWD_HOME}/g' ${CROWD_INSTALL_DIR}/apache-tomcat/bin/setenv.sh

VOLUME ["${CROWD_HOME}"] # Must be declared after setting perms

COPY entrypoint.py \
     shutdown-wait.sh \
     shared-components/image/entrypoint_helpers.py  /
COPY shared-components/support                      /opt/atlassian/support
COPY config/*                                       /opt/atlassian/etc/
