from openerp import models, fields, api
from datetime import date, timedelta, datetime
import tempfile
import pysftp

class MftSsu(models.Model):
    _name = "teds.mft.file"
    _description = "TEDS MFT File"
    
    @api.model
    def create(self,val,context=None):
        object_cek=self.search([('active','=',True)])
        if object_cek and val['active'] == True :
            raise Warning ('Perhatian, Terdapat Configuration Yang Active!')
        return super(MftSsu,self).create(val)
    
    host_remote = fields.Char(string='Host Remote', required=True)
    user_remote = fields.Char(string='User Remote', required=True)
    password_remote = fields.Char(string='Password Remote', required=True)
    folder_path_remote = fields.Char(string='Folder Path Remote',required=True)

    active = fields.Boolean(string='Active')

    @api.multi
    def ssu_received(self):
        yesterday = date.today() - timedelta(days=1)
        # yesterday = datetime.strptime('2015-09-03', '%Y-%m-%d')
        lots = self.env['stock.production.lot'].sudo().search([('receive_date','=',yesterday),('branch_id.code','=','MML')])
        yesterday = yesterday.strftime('%d%m%Y')
        temp_dir = tempfile.gettempdir()
        d = date.today()
        tgl = d.strftime('%Y%m%d')
        name = 'H2Z'+tgl+'IN.SSU'
        local_path = temp_dir+'/'+name
        f= open(local_path,"w+")
        for lot in lots:
            value = ""
            value += "H2Z"
            value += ";%s" % lot.name
            value += ";%s" % lot.chassis_no
            value += ";RFS"
            value += ";%s" % yesterday
            value += ";;;;;;;;;;;;;;;\r\n"
            f.write(value)
        f.close()
        self.send_sftp(local_path)

    @api.multi
    def send_sftp(self, path_file):
        conf_browse = self.sudo().search([('active', '=', True)], limit=1)
        if not conf_browse:
            raise Warning ('Perhatian, Tidak Ada Configuration Yang Active!')
        host = conf_browse.host_remote
        user = conf_browse.user_remote
        password = conf_browse.password_remote
        remote_path = conf_browse.folder_path_remote
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None
        sftp = pysftp.Connection(host, username=user, password=password, cnopts=cnopts)
        sftp.chdir(remote_path)
        sftp.put(path_file)
        sftp.close()