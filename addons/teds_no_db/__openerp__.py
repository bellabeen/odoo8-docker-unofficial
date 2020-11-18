{
    "name"          : "teds no manage db",
    "version"       : "1.0",
    "author"        : "TDM",
    "website"       : "https://honda-ku.com",
    "category"      : "Custom Module",
    "description"   : """
        Remove Link Database Manager, Powered by Odoo, etc.
    """,
    "depends"       : [
        "base",
        "web",
    ],
    "init_xml"      : [],
    "demo_xml"      : [],
    "data"          : [
        'views/teds_no_db.xml',
    ],
    "js"            : [],
    "css"           : [],
    "active"        : False,
    "application"   : True,
    "installable"   : True
}