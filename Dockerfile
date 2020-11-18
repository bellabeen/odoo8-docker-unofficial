FROM odoo:8

USER root

RUN apt-get update -y && \
    apt-get install -y build-essential \
                        autoconf \
                        libtool \
                        pkg-config \
                        python-opengl \
                        python-imaging \
                        python-pyrex \
                        python-pyside.qtopengl \
                        idle-python2.7 \
                        qt4-dev-tools \
                        qt4-designer \
                        libqtgui4 \
                        libqtcore4 \
                        libqt4-xml \
                        libqt4-test \
                        libqt4-script \
                        libqt4-network \
                        libqt4-dbus \
                        python-qt4 \
                        python-qt4-gl \
                        libgle3 \
                        python-dev 
                        # Python-Chart\ 
                        # pyusb \
                        # qrcode
RUN pip install --upgrade pip
# RUN apt-get update -y && \
#         mv /usr/local/lib/python2.7/dist-packages/greenlet* /tmp/

# RUN pip2 uninstall gevent
RUN pip2 install asn1crypto==0.24.0 \
                        Babel \
                        bcrypt==3.1.4 \
                        cachetools==3.1.1 \
                        certifi==2015.4.28 \
                        cffi==1.11.5 \
                        cryptography==2.3.1 \
                        decorator==4.0.9 \
                        docutils==0.12 \
                        enum34==1.1.2 \
                        feedparser==5.2.1 \
                        funcsigs==0.4 \
                        gdata==2.0.18 \
                        gevent \
                        google-api-python-client==1.7.11 \
                        google-auth==1.6.3 \
                        google-auth-httplib2==0.0.3 \
                        google-auth-oauthlib==0.4.1 \
                        greenlet \
                        httplib2==0.14.0 \
                        idna==2.7 \
                        ipaddress==1.0.16 \
                        Jinja2==2.8 \
                        linecache2==1.0.0 \
                        lxml \
                        Mako==1.0.3 \
                        MarkupSafe==0.23 \
                        mock==1.3.0 \
                        ndg-httpsclient==0.5.1 \
                        numpy==1.16.6 \
                        oauthlib==3.1.0 \
                        OdooRPC==0.6.2 \
                        paramiko==2.4.2 \
                        passlib==1.6.5 \
                        pbr==1.8.1 \
                        Pillow \
                        psutil \
                        psycogreen==1.0 \
                        psycopg2 \
                        py-spy==0.3.2 \
                        pyasn1==0.4.7 \
                        pyasn1-modules==0.2.7 \
                        PyChart==1.39 \
                        pycparser==2.14 \
                        pydot==1.0.2 \
                        Pygments==2.1.3 \
                        PyNaCl==1.3.0 \
                        pyOpenSSL==16.2.0 \
                        pyparsing \
                        pyPdf==1.13 \
                        pyserial==3.0.1 \
                        pysftp==0.2.9 \
                        python-dateutil==2.5.0 \
                        python-ldap \
                        python-openid==2.2.5 \
                        python-stdnum==1.2 \
                        pytz==2015.7 \
                        PyWebDAV==0.9.8 \
                        PyYAML==3.11 \
                        reportlab \
                        requests==2.9.1 \
                        requests-oauthlib==1.2.0 \
                        rsa==4.0 \
                        simplejson \
                        six==1.10.0 \
                        traceback2==1.4.0 \
                        unittest2 \
                        uritemplate==3.0.0 \
                        vatnumber==1.2 \
                        vobject==0.9.1 \
                        Werkzeug==0.11.4 \
                        xlrd==0.9.4 \
                        XlsxWriter==0.8.4 \
                        xlwt

USER odoo
ENTRYPOINT [ "/entrypoint.sh" ]
CMD [ "openerp-server" ]