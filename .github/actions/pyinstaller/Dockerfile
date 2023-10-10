FROM cdrx/pyinstaller-windows

COPY ./.github/actions/pyinstaller/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
