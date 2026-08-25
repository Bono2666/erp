FROM odoo17:local

USER root

RUN echo "db_name = erp" >> /etc/odoo/odoo.conf

COPY --chown=odoo:odoo . /opt/odoo/custom-addons

USER odoo
