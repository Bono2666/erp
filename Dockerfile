FROM odoo17:local

USER root

COPY --chown=odoo:odoo . /opt/odoo/custom-addons

USER odoo
