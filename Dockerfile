FROM odoo17:local

USER root

RUN sed -i 's|http_port = 8069|http_port = 8069\ndb_name = erp|' /entrypoint.sh && \
    chmod +x /entrypoint.sh

COPY --chown=odoo:odoo . /opt/odoo/custom-addons

USER odoo
