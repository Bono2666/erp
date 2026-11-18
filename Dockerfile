FROM odoo:17

USER root

# Entrypoint that renders odoo.conf from ODOO_* environment variables
COPY docker/entrypoint.sh /usr/local/bin/erp-entrypoint.sh
RUN sed -i 's/\r$//' /usr/local/bin/erp-entrypoint.sh \
    && chmod 755 /usr/local/bin/erp-entrypoint.sh \
    && chown odoo:odoo /etc/odoo/odoo.conf

# Custom addons. Kept outside /mnt/extra-addons on purpose: that path is a
# VOLUME in the base image, so code copied there would be shadowed by the
# old anonymous volume whenever the container is recreated.
COPY --chown=odoo:odoo . /opt/odoo/custom-addons

USER odoo

EXPOSE 8069 8072

ENTRYPOINT ["/usr/local/bin/erp-entrypoint.sh"]
CMD ["odoo"]
