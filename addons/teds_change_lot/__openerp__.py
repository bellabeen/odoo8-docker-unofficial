# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    "name":"Teds Change Lot",
    "version":"0.2",
    "author":"ASN",
    "website":"teds.tunasdwipamatra.com",
    "category":"TDM",
    "description": """
        Teds Penggantian Data STNK BPKB.
    """,
    "depends":["base","wtc_stock","wtc_dealer_menu","wtc_branch","wtc_approval","mail","stock"],
    "init_xml":[],
    "demo_xml":[],
    "data":[
                "data/teds_approval_config_data.xml",
                "views/teds_change_lot_view.xml",
                "views/teds_lot_view.xml",
                "security/ir_rule.xml",
                "security/res_groups.xml",
                "security/res_groups_button.xml",
                "security/ir.model.access.csv",
                  ],
    "active":False,
    "installable":True
}
