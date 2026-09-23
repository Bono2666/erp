FROM odoo:17

USER root

# Fix line endings untuk Windows
RUN apt-get update && apt-get install -y dos2unix

RUN sed -i 's|http_port = 8069|http_port = 8017\ndb_name = erp|' /entrypoint.sh && \
    chmod +x /entrypoint.sh && \
    dos2unix /entrypoint.sh

COPY --chown=odoo:odoo . /opt/odoo/custom-addons

# Fix line endings untuk semua script
RUN find /opt/odoo/custom-addons -name "*.sh" -exec dos2unix {} \;

USER odoo
