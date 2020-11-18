# -*- coding: utf-8 -*-
from openerp import models, fields, api
class TitikKeramaian(models.Model):
    _name = 'titik.keramaian'
    branch_id = fields.Many2one('wtc.branch', 'Branch', required=True)
    kecamatan_id = fields.Many2one('wtc.kecamatan', 'Kecamatan', required=True)
    ring_id = fields.Many2one('master.ring', 'Ring name', required=True)
    name = fields.Char('Titik Keramaian', required=True)
    latlang = fields.Char('Lat,Lang')
    category = fields.Selection([
            ('Rumah Sakit', 'Rumah Sakit'),
            ('Puskesmas', 'Puskesmas'),
            ('Praktek Dokter','Praktek Dokter'),
            ('Pasar Induk','Pasar Induk'),
            ('Pasar Kaget','Pasar Kaget'),
            ('Pasar Tumpah','Pasar Tumpah'),
            ('Minimarket','Minimarket'),
            ('Supermarket','Supermarket'),
            ('Cafe','Cafe'),
            ('Restaurant','Restaurant'),
            ('Perkantoran','Perkantoran'),
            ('Tempat Wisata','Tempat Wisata'),
            ('Tempat Hiburan','Tempat Hiburan'),
            ('SPBU','SPBU'),
            ('Sekolah atau Universitas','Sekolah atau Universitas'),
            ('Taman Kota','Taman Kota'),
            ('Perkebunan','Perkebunan'),
            ('Perkampungan','Perkampungan'),
            ('Terminal','Terminal'),
            ('Bandara','Bandara'),
            ('Showroom TDM','Showroom TDM'),
            ('Rumah Ibadah','Rumah Ibadah'),
            ],'Category')
    
    @api.onchange('branch_id')
    def kecamatan_id_change(self):
        #vals = []
        self.kecamatan_id = False
        dom = {}
        
        ring_kec_id = self.env['ring.kecamatan'].search([('branch_id','=',self.branch_id.id)]).id
        ring_kec_line = self.env['ring.kecamatan.line'].search([('ring_kecamatan_id','=',ring_kec_id)])
        
        id_list = []
        for record in ring_kec_line:
            id_list.append(record.kecamatan_id.id)
            #vals.append(record.kecamatan_id)
        
        dom['kecamatan_id']=[('id','in',id_list)]
        #return {'value':{'kecamatan_id':vals}}
        return {'domain':dom}
    
    @api.onchange('branch_id', 'kecamatan_id')
    def ring_id_change(self):
        self.ring_id = False
        dom = {}
        
        ring_kec_id = self.env['ring.kecamatan'].search([('branch_id','=',self.branch_id.id)]).id
        ring_kec_line = self.env['ring.kecamatan.line'].search([('ring_kecamatan_id','=',ring_kec_id),
                                                                ('kecamatan_id','=',self.kecamatan_id.id)])
        
        id_list = []
        for record in ring_kec_line:
            id_list.append(record.ring_id.id)
            
        dom['ring_id']=[('id','in',id_list)]
        return {'domain':dom}
        
    #@api.one
    #@api.onchange('branch','kecamatan')
    #def onchange_br_kecamatan(self):
    #    branch_id = self.branch.id
    #    kecamatan_id = self.kecamatan.id
    #    ring_kecamatan = self.env['ring.kecamatan'].search([
    #                                                  ('branch.id','=', branch_id),
    #                                                  ('kecamatan.id','=', kecamatan_id)]).ring.name
    #    self.ring = ring_kecamatan