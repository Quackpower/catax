# -*- coding: utf-8 -*-
from odoo import http, models, fields, api, exceptions
import requests
import pytz
from werkzeug.wrappers import Response
import io, os, re, time
from datetime import datetime, timedelta
from localStoragePy import localStoragePy
import xlwt
from os.path import dirname as up
import math, random
import base64
import logging
import unidecode
import re

logger = logging.getLogger(__name__)
modulePath = up(up(os.path.realpath(__file__)))
class catax(models.Model):
    _name = 'catax.catax'
    _module_prefix = 'CTX'
    _rec_name = 'folio_report'
    
    estatus          = fields.Selection([('R', 'Recibido'), ('enproceso', 'En Proceso'), ('ATEN', 'Atendido')], default='R', string="Estado del reporte", track_visibility=True)
    cerrar_atencion  =  fields.Selection([('RES','Resuelto'),('INC','Información incompleta'),('ERR','Error de captura'),('NEU','No existe la ubicación '),('MND','Material no disponible '),('NCA','No es competencia del Ayuntamiento')], string='Cerrar atención',  track_visibility=True)
    #info del reporte
    folio            = fields.Char(string= "#", track_visibility=True)
    folio_report     = fields.Char(string= "Folio", track_visibility=True)
    categoria        = fields.Many2one("catalogos_catax",ondelete="cascade", string="Categoria del registro", required=True ,track_visibility=True)    
    sub_categoria    = fields.Many2one("subcategorias_catax",ondelete="cascade", string="Sub-Categoria", required=True,track_visibility=True)
    name             = fields.Char(string="Nombre de la persona que reporta", default="Anónimo", track_visibility=True)

    medio_reporte    = fields.Selection([('T', 'Telefonica'),('C', 'Correo'),('R', 'Redes sociales'),('O', 'Escrito/Oficio'), ('W', 'Web')], string="Medio del reporte", required=True, track_visibility=True)

    telefono         = fields.Char("Teléfono",  track_visibility=True)
    correo           = fields.Char(string="Correo electrónico",  default="")
    redsocial        = fields.Selection([('F', 'Facebook'),('T', 'Twitter')], string="Red social del reporte")
    

    municipio        = fields.Selection([('2087', 'Xalapa-Enriquez')], string='Municipio', default="2087", track_visibility=True)
    colonia          = fields.Char(string="Colonia",track_visibility=True)
    calle            = fields.Char(string="Calle", track_visibility=True)
    no_exterior      = fields.Char(string="No. Exterior", track_visibility=True)
    no_interior      = fields.Char(string="No. Interior", track_visibility=True)
    #cp               = fields.Many2one('directions_utils.codigos_postales', domain="[('id_municipio','=', 2087)]", string="Codigo postal", track_visibility=True)
    referencia       = fields.Text(string="Referencia", track_visibility=True)

    #fotografiaReporte = fields.Binary(string="Foto")

    latitud      = fields.Char(string='Latitud', track_visibility=True)
    longitud     = fields.Char(string='Longitud', track_visibility=True)
    address      = fields.Char(string="Dirección", track_visibility=True)

    descripcion_reporte = fields.Text(string="Descripción del reporte", required=True, track_visibility=True)
    desc_report_cort   = fields.Text(string="Descripción del reporte", compute="_get_desc_cort")
    fotografiaReporte = fields.Binary(string="Foto", track_visibility=True)

    observaciones       = fields.Text(string="Observaciones", track_visibility=True)
    comentarios_reporte = fields.One2many('catax.comentarios_apoyo', 'id_catax', string="Comentarios de apoyo", track_visibility=True)
    cant_coment_apoyo   = fields.Integer(string="Cantidad de apoyo" )

   # asignacion del reporte
    #area_categoria          = fields.Many2one("subcategorias_catax.relacion_categoria_areas", string="Área responsable")
    #id_depto_aux            = fields.Integer(related="area_categoria.id_depto.id")                                                                            
    #responsable_area        = fields.Many2one('hr.employee', string="Empleado asignado", track_visibility=True)
    comentario_seguimiento  = fields.Text(string="Comentarios de seguimiento (publico)", track_visibility=True) 
    comentario_area         = fields.Text(string="Comentarios de area", track_visibility=True) 

    fecha_recepcionarea     = fields.Date(string="Fecha recepción", track_visibility=True)
    fecha_estimada          = fields.Date(string="Fecha estimada de atención", track_visibility=True)
    fecha_finalizada        = fields.Date(string="Fecha finalizada", track_visibility=True)
    prioridad_reporte  = fields.Selection([('alta', 'Alta (24 horas)'), ('media', 'Media (72 horas)'), ('baja', 'Baja (Máximo 10 días)')], string="Prioridad")



    calificacion_atencion =  fields.Selection([('0', 'No registrada'),('1', 'Mala'),('2', 'Regular'),('3', 'Suficiente'),('4', 'Buena'),('5', 'Excelente')], default="0",string= 'Calificación de la atención recibida',readonly=True)
    calificacion_reporte =  fields.Selection([('0', 'No registrada'),('1', 'Mala'),('2', 'Regular'),('3', 'Suficiente'),('4', 'Buena'),('5', 'Excelente')], default="0",string= 'Resolución del problema reportado',readonly=True)
    encuesta_enviada      = fields.Boolean()
    eval_calif            = fields.Boolean()
    fecha_encuesta_evaluada = fields.Date(string="Fecha de encuesta evaluada", track_visibility=True)
    comentarios_reportante  = fields.Text(string="Comentarios del usuario", readonly=True) 
    encuesta_contestada_reiterativo = fields.Integer(default=0)

    #Atencion evidencia
    evidencia_atencion = fields.One2many('catax.evidencia_atencion', 'id_report', string='Evidencia de atención')

    

    @api.model
    def _get_operador(self):
        res_user = self.env['res.users'].search([('id', '=', self._uid)])
        return res_user.has_group('catax.operador')

    @api.model
    def _get_analis(self):
        res_user = self.env['res.users'].search([('id', '=', self._uid)])
        return not res_user.has_group('catax.operador')

    is_operador = fields.Boolean(compute='check_user_group',  default=lambda self: self._get_operador() )
    is_analist = fields.Boolean(compute='check_user_group',  default=lambda self: self._get_analis() )
    permisos_extendidos_operador = fields.Boolean(compute='check_user_group') 
    cve_categoria = fields.Char(string="Clave de categoria", related ="categoria.clave" )
    cve_subcategoria = fields.Char(string="Clave de sub-categoria", related ="sub_categoria.clave" )

    recanalizar = fields.Boolean(string="Recanalizar",  default=False)
    solicitar_intervencion_catastro = fields.Boolean(string="Solicitar intervención de Catastro",  default=False)



    def _get_desc_cort(self):  
        for ix in self:
            if ix.descripcion_reporte:
                ix.desc_report_cort = ix.descripcion_reporte[:30] + '...'
        #if self.descripcion_reporte:
        #    self.desc_report_cort = self.descripcion_reporte[:30] + '...'


 
    def check_user_group(self):
        res_user = self.env['res.users'].search([('id', '=', self._uid)])
        self.is_operador = False
        self.permisos_extendidos_operador = False
        if res_user.has_group('catax.operador') or res_user.has_group('catax.operador_ejecutivo'):
            self.is_operador = True
        else:
            self.is_operador = False
        if not res_user.has_group('catax.operador')  or not res_user.has_group('catax.operador_ejecutivo'):
            self.is_analist = True
        else:
            self.is_analist = False

        if (res_user.has_group('catax.otro') or res_user.has_group('catax.otro_ejecutivo')) and self.is_operador:
            self.permisos_extendidos_operador = True


    
    @api.model
    def create(self, values):
        self.sanitizador_inyeccion(values)
        try:
            localStorage = localStoragePy('catax_map')
            logger.info(values)
            if 'latitud' in values and 'longitud' in values:
                if values['latitud'] == False and values['longitud'] == False:
                    if localStorage.getItem('latitud') != 'False' and localStorage.getItem('latitud') is not None:
                        values['latitud'] = str(localStorage.getItem('latitud'))
                        localStorage.removeItem('latitud')
                    if localStorage.getItem('longitud') != 'False' and localStorage.getItem('longitud') is not None:
                        values['longitud'] = str(localStorage.getItem('longitud'))
                        localStorage.removeItem('longitud')
                    if localStorage.getItem('direccion') != 'False' and localStorage.getItem('direccion') is not None:
                        values['address'] = str(localStorage.getItem('direccion'))
                        localStorage.removeItem('direccion')

            if 'calle' in values:
                logger.info(localStorage.getItem('calle'))
                
                if values['calle']==False and localStorage.getItem('calle') != 'False' and localStorage.getItem('calle') is not None:
                    values['calle'] = str(localStorage.getItem('calle'))
                    localStorage.removeItem('calle')

            if values['calle']=="undefined":
                values['calle'] = False

            if 'colonia' in values:
                if values['colonia']==False and localStorage.getItem('colonia') != 'False' and localStorage.getItem('colonia') is not None:
                    values['colonia'] = str(localStorage.getItem('colonia'))
                    localStorage.removeItem('colonia')

            if 'correo' in values and values['correo']:
                values['correo'] = unidecode.unidecode(values['correo'])
                values['correo'] = re.sub(u"[ñ]", 'n', values['correo'])

            

            if values['latitud'] == False and values['longitud'] == False:
                values['latitud'] = "19.4544924"
                values['longitud'] = "-96.9601074"
            


            functions = self.env['subcategorias_catax.folios']
            folio_r = str(self.get_folio())
            while len(self.env['catax.catax'].search([('folio_report', '=', folio_r)]))>0:
                folio_r = str(self.get_folio())

            values['folio'] = functions.get_folio('catax.catax')
            values['folio_report'] = folio_r
        except Exception as er:
            raise exceptions.Warning(str(er))

        record = super(catax, self).create(values)
        try:
            if record.correo and record.correo.strip() != '':
                self.mandarmsjs_creacion(record.folio_report, record.sub_categoria, record.correo)
        except:
            pass  

        
        return record
        
    def write(self, vals):
        self.sanitizador_inyeccion(vals)
        localStorage = localStoragePy('catax_map')
        logger.info(vals)
        if 'latitud' in vals:
            if localStorage.getItem('latitud') != 'False' and localStorage.getItem('latitud') is not None:
                vals['latitud'] = str(localStorage.getItem('latitud'))
                localStorage.removeItem('latitud')
            elif vals['latitud'] == False:
                vals['latitud'] = ''
        else:
            if localStorage.getItem('latitud') != 'False' and localStorage.getItem('latitud') is not None:
                vals['latitud'] = ''
                vals['latitud'] = str(localStorage.getItem('latitud'))
                localStorage.removeItem('latitud')
            elif 'latitud' in vals and vals['latitud'] == False  and localStorage.getItem('latitud') is not None:
                vals['latitud'] = ''

        if 'longitud' in vals:
            if localStorage.getItem('longitud') != 'False' and localStorage.getItem('longitud') is not None:
                vals['longitud'] = str(localStorage.getItem('longitud'))
                localStorage.removeItem('longitud')
            elif vals['longitud'] == False:
                vals['longitud'] = ''
        else:
            if localStorage.getItem('longitud') != 'False' and localStorage.getItem('longitud') is not None:
                vals['longitud'] = ''
                vals['longitud'] = str(localStorage.getItem('longitud'))
                localStorage.removeItem('longitud')
            elif 'longitud' in vals and vals['longitud'] == False:
                vals['longitud'] = ''

        if 'address' in vals:
            if localStorage.getItem('direccion') != 'False' and localStorage.getItem('direccion') is not None:
                vals['address'] = str(localStorage.getItem('direccion'))
                localStorage.removeItem('direccion')
            elif vals['address'] == False and localStorage.getItem('address') != None:
                vals['address'] = ''
        else:
            if localStorage.getItem('direccion') != 'False' and localStorage.getItem('direccion') is not None:
                vals['address'] = ''
                vals['address'] = str(localStorage.getItem('direccion'))
                localStorage.removeItem('direccion')
            elif 'address' in vals and vals['address'] == False:
                vals['address'] = ''

        if 'calle' in vals:
            if localStorage.getItem('calle') != 'False' and localStorage.getItem('calle') is not None:
                if vals['calle'] == False or vals['calle'] == "":
                    vals['calle'] = str(localStorage.getItem('calle'))
                localStorage.removeItem('calle')
            elif 'calle' in vals and vals['calle'] == False and localStorage.getItem('calle') is not None:
                vals['calle'] = ''
        else:
            if localStorage.getItem('calle') != 'False' and localStorage.getItem('calle') is not None:
                vals['calle'] = str(localStorage.getItem('calle'))
                localStorage.removeItem('calle')
            elif 'calle' in vals and vals['calle'] == False:
                vals['calle'] = ''

        if 'colonia' in vals:
            if localStorage.getItem('colonia') != 'False' and localStorage.getItem('colonia') is not None:
                if vals['colonia'] == False or vals['colonia'] == "":
                    vals['colonia'] = str(localStorage.getItem('colonia'))
                localStorage.removeItem('colonia')
            elif 'colonia' in vals and vals['colonia'] == False and localStorage.getItem('colonia') is not None:
                vals['colonia'] = ''
        else:
            if localStorage.getItem('colonia') != 'False' and localStorage.getItem('colonia') is not None:
                vals['colonia'] = str(localStorage.getItem('colonia'))
                localStorage.removeItem('colonia')
            elif 'colonia' in vals and vals['colonia'] == False:
                vals['colonia'] = ''

        
                
        record = super(catax, self).write(vals)
        
        
        return record

    def get_folio(self):
        alfa = ""
        finStr = ''
        posible = "ABCDEFGHJKLMNPQRSTUVWXYZ123456789"
        
        a = datetime.now()
        a = int(a.strftime('%Y%m%d'))
        actual = str(math.floor(a / 1000)).replace('0','1')

        for i in range(0, 10):
            alfa += posible[math.floor(random.random() * len(posible))]
    
        final = alfa[1:2] + actual[7:8] + actual[0:1] + alfa[8:9] + actual[2:3] + alfa[6:7] + actual[4:5] + alfa[4:5] + actual[6:7] + alfa[2:3] + actual[8:9] + alfa[0:1] + alfa[1:2]

        a = list(final)

        random.shuffle(a)
        finStr = ''.join(a)

        return finStr[:6]

    @api.model
    def filter_tree_by_department(self, context):        
        if context is None:
            context = {}
        #is_group_directivo = self.env['res.users'].has_group('seguimiento_solicitudes.ejecutivo') # Instruccion 

        #if is_group_directivo:
        #    domain = ''
        #    visuallizacion = 'graph,tree,form'
        #else:
        user = self.env['res.users'].search([('id', '=', self._uid)])
        employee = self.env['hr.employee'].search([('partner_id', '=', user.partner_id.id)])
        context.update({'_department_name': employee.department_id.name,'form_view_ref': 'seguimiento_solicitudes.subsolicitudes_form_operativo'})
        self.with_context(_department_name=employee.department_id.name)
        domain = [('area_asignad', '=',employee.department_id.id)] #,('estatus', 'in', ['turnada', 'en_proceso','atendida'])
        visuallizacion = 'tree,form,graph'
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'catax.catax',
            'name': 'Solicitudes CATAX',
            'view_mode': visuallizacion,
            'target': 'self',
            'domain': domain,
            'context': context,
        }

    def change_estatus(self, context):
        if str(context['estatus']) =='ATEN':
            if not self.cerrar_atencion:
                raise exceptions.Warning("Imposible pasar el reporte a atendido sin seleccionar el cierre de atención.")
            self.fecha_finalizada= datetime.now().astimezone(pytz.timezone('Mexico/General'))
            message_bytes = str(self.folio_report).encode('ascii')
            fol_link = "https://catax.xalapa.gob.mx/califica/?fol=" + str(base64.b64encode(message_bytes)).split("'")[1]
            encabezado = 'Reporte atendido'
            if not self.comentario_seguimiento:
                raise exceptions.Warning("Debe escribir un comentario de seguimiento para retroalimentación del ciudadano.")
            texto = 'Su reporte con folio <b>' + self.folio_report + '</b> de la categoría <i>' + self.categoria.display_name + '</i> ha sido atendido. <br/>Con las siguientes anotaciones: </br><p>'+self.comentario_seguimiento+'</p></br>'
            self.send_correcoelect(texto, encabezado, False,True,fol_link)
            logger.info('4')
            #self.encuesta_enviada = True            
        self.estatus = str(context['estatus'])

    def estatus_en_proceso(self):    
        self.estatus = 'enproceso'

    def estatus_atendido(self):
        if not self.cerrar_atencion:
            raise exceptions.Warning("Imposible pasar el reporte a atendido sin seleccionar el cierre de atención.")
        self.fecha_finalizada= datetime.now().astimezone(pytz.timezone('Mexico/General'))
        
        encabezado = 'Reporte atendido'
        if not self.comentario_seguimiento:
            raise exceptions.Warning("Debe escribir un comentario de seguimiento para retroalimentación del ciudadano.")
        texto = 'Su reporte con folio <b>' + self.folio_report + '</b> ha sido atendido. <br/>Con las siguientes anotaciones: </br><p>'+self.comentario_seguimiento+'</p></br>'
        self.send_correcoelect(texto, encabezado, False,True)
  
        self.estatus = 'ATEN'

    def mandarmsjs_creacion(self, folio, id_subcatgoria, email_aux):
        aux_subcat= self.env['subcategorias_catax'].search([('id', '=', id_subcatgoria.id)])
        categoria       = aux_subcat.categoria.name
        sub_categoria   = aux_subcat.name
        encabezado = 'Reporte registrado en CMAS con folio ' + folio
        texto = 'Su reporte <i>' + sub_categoria + '</i> ha sido registrado correctamente en el Sistema de reportes CMAS con el siguiente folio:  <br/>  <h2 style="color:#a53420;text-align:center;"><b>' + folio + '</b></h2>  Mediante este número de folio, podrá darle seguimiento a su reporte.'
        self.send_correcoelect(texto, encabezado, email_aux,False)

    def send_correcoelect(self, textbody, asunto, email_aux,adjuntar_evidencia,link_encuesta=False):
        template_id = self.env.ref('catax.email_template_notificaciones_reporte', False)
        if not email_aux:
            correo_enviar =  self.correo
        else:
            correo_enviar = email_aux
        if self.env['ir.config_parameter'].search([('key', '=', 'web.base.url')]).value != 'http://reportescatax.xalapa.gob.mx':
            msj_prueba = asunto + ' (Este correo fue mandado desde un entorno de pruebas)'
        else:
            msj_prueba = asunto   

        template = self.env['mail.template'].browse(template_id.id)
        template.attachment_ids = False
        if adjuntar_evidencia:
            attachment_ids = []
            try:
                archivos = self.evidencia_atencion
                
                
                for x in archivos:
                    logger.info(x.nombre_archivo)

                    if not x.evidencia:
                        raise exceptions.Warning("Debe adjuntar un archivo por cada fila en la sección de evidencias.")

                    attachment = {
                        'name': str(x.filename),
                        'store_fname': x.filename,
                        'res_model': 'catax.evidencia_atencion',
                        'datas':x.evidencia,
                        'type': 'binary'
                    }

                    attch = self.env['ir.attachment'].create(attachment)
                    attachment_ids.append(attch.id)
                
                if attachment_ids:
                    template.write({'attachment_ids': [(6, 0, attachment_ids)]})
                    textbody = textbody +  " Se adjunta al presente correo electrónico la documentación digital correspondiente como evidencia. <br/>  " 
                else:
                    textbody =  textbody 
            except Exception as er:
                hasFileAttach=False
                raise Warning("No se puede enviar correo de contestación, error en la recuperación del archivo - " + str(er))

        mail_values = {
            'asunto_correo': msj_prueba ,
            'correo': correo_enviar,
            'body_txt': textbody
        }
        local_context = self.env.context.copy()
        local_context.update(mail_values)

        template.sudo().with_context(local_context).send_mail(self.id, raise_exception=True, force_send=True)

    @api.model
    def panel_control(self, context):
        # se agrega el caso que ahora un capturista pueda ver las estadisticas de los registros que ha realizado Jorge Luis 07/09/2019
        
        if context is None:
            context = {}
        # user = self.env['res.users'].search([('id', '=', self._uid)])
        # employee = self.env['hr.employee'].search([('partner_id', '=', user.partner_id.id)])        
        # base_group = self.env.ref('seguimiento_solicitudes.operativo')
        # base_groupCaptu = self.env.ref('seguimiento_solicitudes.capturista')#Si es un capturista obtengo todos los usuarios Jorge Luis 07/09/2019
        # areas = self.search([])
        # areascaptu = self.search([('departamentoRegiduria','=',employee.department_id.id)]) # solo busco por departamento de un capturista Jorge Luis 07/09/2019
        # areas = areas.mapped('departamentoAreaOperativaDireccion').ids
        # areascaptu = areascaptu.mapped('departamentoAreaOperativaDireccion').ids
        # areas = list(dict.fromkeys(areas))
        # areascaptu = list(dict.fromkeys(areascaptu))# Jorge Luis 07/09/2019
        # if (self._uid in base_group.users.ids): # si es un usuario operativo
        #     domain = ['|',('parent_id', '=', False),('nivel','=','direccion'),('name', '=', employee.department_id.name)]
        # elif self._uid in base_groupCaptu.users.ids: # si es un usuario capturista Jorge Luis 07/09/2019
        #     domain = ['|',('parent_id','=',False),('parent_id','=','Tesorería'),('name','not in',self.regidurias),('id','in',areascaptu)]
        # else: # si es un directivo 
        domain = ['|',('parent_id','=',False),('parent_id','=','Tesorería')] #,('name','not in',self.regidurias)

        context.update({'kanban_view_ref': 'catax_custom_kanban'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.department',
            'name': 'Estadistica de solicitudes',
            'view_type': 'kanban',
            'view_mode': 'kanban',
            'target': 'self',
            'domain': domain,
            'context': context,
        }

    def get_total_requested(self, id):
        rec = self.env['hr.department'].browse(id) 
        #base_group = self.env.ref('seguimiento_solicitudes.operativo')        
        #if self._uid in base_group.users.ids:
        #    return self.env['seguimiento_solicitudes.sub_solicitud'].search_count([('departamentoAreaOperativaDireccion', '=', rec.id),('estatus', '!=', 'nuevo')])            
        #else:
        #user = self.env['res.users'].search([('id', '=', self._uid)])
        #employee = self.env['hr.employee'].search([('partner_id', '=', user.partner_id.id)])
        #if not employee.department_id.id:
        return self.env['catax.catax'].search_count([('area_asignad', '=', rec.id), ('estatus', '!=', 'R')])    
        #else:
        #    return self.env['catax.catax'].search_count([('area_asignada', '=', rec.id), ('estatus', '!=', 'recibido'),('departamentoRegiduria','=',employee.department_id.id)])    

    def get_resolved_requested(self, id):
        rec = self.env['hr.department'].browse(id)        
        #base_group = self.env.ref('seguimiento_solicitudes.operativo')
        #if self._uid in base_group.users.ids:
        #    return self.env['seguimiento_solicitudes.sub_solicitud'].search_count([('departamentoAreaOperativaDireccion', '=', rec.id),('estatus', '=', 'atendida')])        
        #else:
        #user = self.env['res.users'].search([('id', '=', self._uid)])
        #employee = self.env['hr.employee'].search([('partner_id', '=', user.partner_id.id)])
        #if not employee.department_id.id:
        return self.env['catax.catax'].search_count([('area_asignad', '=', rec.id), ('estatus', '=', 'atendida')]) # '|','&amp;',   ,'&amp;',,('estatus', '!=', 'nuevo')
        #else:
        #    return self.env['catax.catax'].search_count([('area_asignada', '=', rec.id), ('estatus', '=', 'atendida'),('departamentoRegiduria','=',employee.department_id.id)])    

    def sanitizador_inyeccion(self, values):
        for x in values:
            if type(values[x]) == str and not 'fotografiaReporte' in values and not 'correo' in values:
                texto = values[x]                
                texto = texto.replace(" OR ", " o ").replace(' Or ',' o ').replace(' oR ',' o ').replace(' or ', ' o ').replace('--', '-').replace('$', '').replace("'", '').replace("=", '').replace(";", '').replace("?", '').replace("|", '').replace("from", 'desde').replace("=", '')
                texto = texto.replace("<", "").replace('>','').replace('/','').replace("\\",'').replace("&lt;",'').replace("&quot;",'').replace("&",'')
                values[x] = texto

    def change_canalizado(self, params):
        if self.recanalizar:
            if str(params['recanalizar']) == 'False':
                self.recanalizar = False

    def consulta_encuesta_contestada(self):
        err = ''
        try:
            faltante_encuesta = self.sudo().search([('eval_calif', '=', False), ('estatus', '=', 'ATEN'),('correo', '!=', ""),('encuesta_contestada_reiterativo', '<', 4)])

            format_str = '%Y-%m-%d' 
            
            for x in faltante_encuesta:   
                hoy = datetime.today() 
                fecha_fin = datetime.strptime(x.fecha_finalizada, format_str)

                #if (hoy - timedelta(days=7))>fecha_fin:
                if ( (hoy - timedelta(days=7))>fecha_fin and (hoy - timedelta(days=8))<fecha_fin) or ( (hoy - timedelta(days=14))>fecha_fin and (hoy - timedelta(days=15))<fecha_fin) or ( (hoy - timedelta(days=21))>fecha_fin and (hoy - timedelta(days=22))<fecha_fin):
                    logger.info("Enviando correo a : ID -" + str(x.id) + " Correo - " + str(x.correo) + " Intento - " + str(x.encuesta_contestada_reiterativo +1))

                    message_bytes = str(x.folio_report).encode('ascii')
                    fol_link = "https://catax.xalapa.gob.mx/califica/?fol=" + str(base64.b64encode(message_bytes)).split("'")[1]
                    encabezado = 'Encuesta de satisfacción CATAX'
                    texto = 'Su reporte con folio <b>' + x.folio_report + '</b> de la categoría <i>' + x.categoria.display_name + '</i> fue atendido el pasado '+datetime.strptime(x.fecha_finalizada, "%Y-%m-%d").strftime("%d-%m-%Y")+'.<br/>Con las siguientes anotaciones: <br/> <p>'+self.comentario_seguimiento+'</p></br> '
                    
                    self.send_correcoelect(texto, encabezado, x.correo,False,False)

                    reg = self.sudo().search([('id', '=', x.id)])
                    reg.sudo().write({
                        'encuesta_contestada_reiterativo' : x.encuesta_contestada_reiterativo+1,
                    })

            logger.info("Consulta encuestas contestadas termino de ejecutarse")
        except Exception as er:
            logger.info("Error en Consulta encuestas contestadas termino de ejecutarse" + str(er))

class comentarios_apoyo(models.Model):
    _name = 'catax.comentarios_apoyo'

    id_catax     = fields.Many2one('catax.catax', string='Folio de reporte',ondelete="cascade")
    folio        = fields.Char(string="Folio del reporte")
    comentarios  = fields.Char(string="Comentarios de apoyo")
    correo_apoyo = fields.Char(string="Correo electrónico de apoyo", default="")
    
    @api.model
    def create(self, values):
        try:
            ok = super(comentarios_apoyo, self).create(values)

            catax_id = self.env['catax.catax'].sudo().search([('id','=', values['id_catax'])])
            data = {
                'cant_coment_apoyo' : catax_id.cant_coment_apoyo+1
            }
            catax_id.write(data)
            return ok
        except Exception as er:
            raise exceptions.Warning(str(er))

class catax_evidencia_atencion(models.Model):
    _name = 'catax.evidencia_atencion'
    id_report          = fields.Many2one("catax.catax", string="Reporte",ondelete="cascade")
    nombre_archivo = fields.Char(string="Descripción")
    evidencia = fields.Binary(string="Evidencia de atención")
    filename = fields.Char()

    @api.constrains('filename')
    def _check_filename(self):
        white_list = ['pdf','jpg','jpeg','png','xls','ods','mp4','avi','doc','docx']
        logger.info('general')
        if self.evidencia:
            ext = self.filename.split('.')[-1]
            logger.info('extension')
            logger.info(ext)
            if ext not in white_list:
                raise exceptions.Warning("No puede subir un archivo con esa extensión, sólo puede subir  archivos de imagen o pdf.")
        else:
            ext = self.filename.split('.')[-1]
            logger.info('extension')
            logger.info(ext)
            if ext not in white_list:
                raise exceptions.Warning("No puede subir un archivo con esa extensión, sólo puede subir  archivos de imagen o pdf.")



class historial_asignacion_areas(models.Model):
    _name = 'catax.historial_asignacion_areas'

    comentario_seguimiento  = fields.Text(string="Comentarios de seguimiento (publico)", track_visibility=True) 
    comentario_area         = fields.Text(string="Comentarios de area", track_visibility=True) 

class reportes_catax(models.TransientModel):
    _name = "catax.reportes"

    tipo_reporte = fields.Selection([('C', 'Informe general'), ('T', 'Informe encuesta de satisfacción')], string='Tipo de reporte')
    reporte_oficial = fields.Selection([('O', 'Informe Oficial'), ('I', 'Informe interno')], string='Tipo de reporte general', default="O")
    fecha_ini    = fields.Date(string='Fecha inicial')
    fecha_fin    = fields.Date(string='Fecha final' )

    def genera_titulos(self, ws, titulos, style):
        cont = 0        
        cantidad_columna = len(titulos)
        #Merge del titulo
        ws.write_merge(0, 0, 0, (cantidad_columna*2)-3, 'CATAX - reporte de casos y atención en los Servicios Municipales',style=style)

        x = 0
        for tit in titulos:   
            if cont==0 or x == cantidad_columna-1: #area y ultima columa de casos acuumulados
                ws.write_merge(1, 2 , cont, cont, tit, style=style)
                cont+= 1
            else:              
                ws.write_merge(1, 1,cont,(cont+1), tit, style=style)
                ws.write(2,cont,'Reportes recibidos' ,style=style)
                ws.write(2,cont+1,'Reportes atendidos' ,style=style)
                cont+= 2   

            if x<3:
                ws.row(x).height_mismatch = True
                ws.row(x).height = 600
            x+=1    

    def busqueda_count_catax(self, model_search, fecha_ini, fecha_fin, categorias, estatus=[], atendidas = False, where_add =False):
        """ Jorge Luis Lopez Cruz
        Esta funcion es para facilitar el search count (contar los registros) en la base de datos con los parametros necesarios

        """
        if not atendidas:  
            campo_rango = 'create_date'
        else: 
            campo_rango = 'fecha_finalizada'
        where = [(campo_rango,'>=', fecha_ini.strftime("%Y-%m-%d")),(campo_rango, '<=', fecha_fin.strftime("%Y-%m-%d") ), ('categoria', 'in', categorias)]
        if estatus:
            where.append(('estatus', 'in', estatus))
        if where_add:
            where.append(where_add)

        total_registros = model_search.sudo().search_count(where)
        return total_registros

    def date2str(self, output_format, input_date = False, external_user = False):
        """
        H.Stivalet 2019-05-25
        Función que regresa parte de la fecha si no recibe la fecha usa la fecha actual, usa formato de fecha de python y el comodín "full" para imprimir de menera textual la fecha completa
        params:
        	output_format: (str) Formato de salida (ej. '%Y-%m-%d') usar comodín full para mostrar la fecha en formato de oracion (ej. 25 de Mayo de 2019)
        	input_date: (date | str) Fecha actual a convertir
        returns: (str) Fecha formateada de acuerdo al output_format.
        """
        if not input_date:
            input_date = datetime.now()
            tz = 'Mexico/General'
        else:
            tz = 'Mexico/General' if external_user else ''
        if not input_date: # Si input date es falso le asigna la fecha actual
            input_date = datetime.now()
        if isinstance(input_date, str):
            if input_date.find(':') == -1:
                input_date = datetime.strptime(input_date, '%Y-%m-%d')
            else:
                input_date = datetime.strptime(input_date, '%Y-%m-%d %H:%M:%S')
        if tz and tz != '':
            input_date = input_date.astimezone(pytz.timezone(tz))
        if output_format.upper() == 'FULL':
            return input_date.strftime('%d') + ' de ' + self.month_converter( int(input_date.strftime('%m'))) + ' de ' + input_date.strftime('%Y')
        elif output_format.upper() == 'FULLTIME': # H.Stivalet 13/09/2019 Se agrega fecha en texto + hora
            output_txt = input_date.strftime('%d') + ' de ' + input_date.strftime('%B') + ' de ' + input_date.strftime('%Y') + ' a '
            output_txt = output_txt + 'la ' if input_date.strftime('%H') == '1' else output_txt + 'las '
            output_txt = output_txt + input_date.strftime('%H:%M') + ' hrs'
            return output_txt
        else:
            return input_date.strftime(output_format)

    def month_converter(self, month):
        months = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        return months[month- 1]

    def validate_daterange(self, date1, date2, only_date = True):
        """
            Creado por H.Stivalet
            Fecha de Creación: 2019-10-22
            Descripción: Valida el rango de fechas
            args:
            	date1(str): Str de la fecha inicial
            	date2(str): Str de la fecha final
            return(Bool): Folio correspondiente del modelo
        """
        result = False
        try:
            if only_date:
                result = datetime.strptime(date1, '%Y-%m-%d') < datetime.strptime(date2, '%Y-%m-%d')
            else:
                result = datetime.strptime(date1, '%Y-%m-%d %H:%M:%S') < datetime.strptime(date2, '%Y-%m-%d %H:%M:%S')
            return result
        except Exception as er:
            raise er        

    def generate_report_catax(self):
        #id de categorias 
        # 3 = alumbrado (ALUM), 4 = Mantenimiento vial (OBRA), 5 = Parques y Jardines (PARQ), 6 = Limpia Pub (RRSU), 7 = Arbolizado urbano (ARBO), 8 = Reforestacion (REFO), 9 =  Propuesta ciudadana(PROC), 10 = Agua (CMAS)
        # direcciones (Categorias): CMAS (10),  Subdirección de Gestión de Energía (3), Dirección de Obras Púbilcas (4), Subdirección de Recursos Naturales y Cambio Climático (5, 7, 8), Gestión Integral de Residuos Sólidos (6), Dirección de Gobierno Abierto (9)            
            nombre_file = "Informe_general_" + str(self.date2str('full', datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            file_output_name = nombre_file + '.ods'
            template_path = os.path.join(modulePath, 'reports')
            output_template_path = os.path.join(template_path, file_output_name)
            model_catax = http.request.env['catax.catax']
            wb = xlwt.Workbook()
            ws = wb.add_sheet("Informe general")

            # Crear cabecera del excel
            style_cabecera = xlwt.easyxf('font: bold 1,height 200;borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin; align: vert center, horiz center;  alignment: wrap True;font: colour white, bold True;pattern: pattern solid, fore_colour dark_red;')

            style_resultados = xlwt.easyxf('align: horiz left, vert distributed; borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;align: vert center, horiz center; alignment: wrap True')
            
            style_totales = xlwt.easyxf('align: horiz left, vert distributed; borders: top_color black, bottom_color black, right_color black, left_color black,\
                              left thin, right thin, top thin, bottom thin;align: vert center, horiz center; alignment: wrap True; font: bold True; ')                              

            
            fila_areas  = ['Gestión de Energía','Gestión Integral de Residuos Sólidos', 'Recursos Naturales y Cambio Climático', 'Supervisión y Protección Ambiental', 'CMAS', 'Obras Públicas', 'Atención Ciudadana', 'SIPINNA', 'Desarrollo urbano','DIF Municipal','Comercio','Protección civil','Recaudación','Registro civil','Seguridad Ciudadana y Tránsito Municipal','TOTAL']            
            
            if self.tipo_reporte == 'C':
                inicio_datos_fila = 3
                titulos_rep = [ 'Área / Fecha de corte semanal' ]
                semana_inicio_catax= model_catax.sudo().search([],  limit=1, order="create_date asc").create_date # 9-abr-2021 Jorge L.- realizo la busqueda del primer registro en catax para calcular la fecha de inicio del sistema (salida a produccion)
                #sem_ini_catax = datetime.strptime(semana_inicio_catax, '%Y-%m-%d %H:%M:%S').date().isocalendar()[1] # 9-abr-2021 Jorge L.- calculo la semana del año en la que se lanzo catax
                sem_ini_catax = 1
                anno_lanzamiento = 2022 # 9-abr-2021 Jorge L.- como constante pongo el año en la que salio catax para pode calcular por año
                cadena_fechaini = '%s %s %s' % ('2022', str(sem_ini_catax), '1') # 9-abr-2021 Jorge L.- esta varible es un axiliar, cuya estructura es el año en que salio a produccion catax, la semana del año y el dia 1 (Lunes) 
                fecha_inicio = datetime.strptime(cadena_fechaini, '%Y %W %w') # 9-abr-2021 Jorge L.- anteriormente obtenida la semana del año en la que salio a produccion CATAX calculo su primer lunes, y obtengo la fecha
                semana_annoactual = datetime.now().isocalendar()[1] # 9-abr-2021 Jorge L.- obtengo la el numero de la semana del año en la que estamos
                anno_actual =  int(datetime.now().year)   # 9-abr-2021 Jorge L.- saco el año actual
                for j in range(len(fila_areas)): # 9-abr-2021 Jorge L.- este for sirve para imprimir todas las areas que existen incluyendo el total
                    ws.row(inicio_datos_fila+j).height_mismatch = True 
                    ws.row(inicio_datos_fila+j).height = 500    
                    ws.col(0).width = 8000       # 9-abr-2021 Jorge L.- asigno ancho de columna
                    if fila_areas[j] == 'TOTAL':
                        ws.write(inicio_datos_fila + j, 0, fila_areas[j], style=style_totales) # 9-abr-2021 Jorge L.- imprimo valor
                    else:
                        ws.write(inicio_datos_fila + j, 0, fila_areas[j], style=style_resultados) # 9-abr-2021 Jorge L.- imprimo valor

                if anno_actual == anno_lanzamiento:  # 9-abr-2021 Jorge L.- reviso si fue lanzado el mismo año realizo el calculo.                    
                    calculo_sem_anno =  (semana_annoactual - sem_ini_catax)  # 9-abr-2021 Jorge L.- calculo cuantas semanas han pasado desde la semana que salio a produccion catax
                    if self.reporte_oficial == 'I':
                        calculo_sem_anno += 1
                    no_columna_ocupada = 0   # 9-abr-2021 Jorge L.- inicializo el numero de la columna ocupada, esta variable sirve para sabes que columna ya tiene valor y no sobre escribir ya que manda error
                    total_aten_cmas = 0
                    total_reci_cmas = 0
                    total_aten_ge = 0
                    total_reci_ge = 0
                    total_aten_op = 0
                    total_reci_op = 0
                    total_aten_rc = 0
                    total_reci_rc = 0
                    total_aten_spa = 0
                    total_reci_spa = 0
                    total_aten_gesti = 0
                    total_reci_gesti = 0
                    total_aten_atenc = 0
                    total_reci_atenc = 0

                    total_aten_sipinna = 0
                    total_reci_sipinna = 0

                    total_aten_du = 0
                    total_reci_du = 0

                    total_aten_dm = 0
                    total_reci_dm = 0

                    total_aten_mc = 0
                    total_reci_mc = 0

                    total_aten_pc = 0
                    total_reci_pc = 0

                    total_aten_cm = 0
                    total_reci_cm = 0

                    total_aten_reg_civ = 0
                    total_reci_reg_civ = 0

                    total_aten_segu = 0
                    total_reci_segu = 0
                    

                    for i in range(calculo_sem_anno):  # 9-abr-2021 Jorge L.- hago un for mediante las semanas transcurridas desde el lanzamiento de catax
                        fecha_calculada = '%s %s %s' % (str(anno_actual), str(sem_ini_catax+i), '1')  # 9-abr-2021 Jorge L.- variable auxiliar para ir calculando la semana del año desde que salio catax hasta la semana actual, cuya estructura es el año , la semana del año y el dia 1 (Lunes)
                        fechaini_semana = datetime.strptime(fecha_calculada, '%Y %W %w') # 9-abr-2021 Jorge L.- calculo el dia lunes de la semana del año. aqui se obtendra todos los dias lunes desde que salio catax hasta la semana actual
                        fechafin_semana = fechaini_semana + timedelta(days=6)  # 9-abr-2021 Jorge L.- Aqui se calcula todos los domingos de la semana en la que salio catax a la actualidad
                        fecha_letra = '%s-%s-%s' % (fechafin_semana.strftime("%d"),self.month_converter(int(fechafin_semana.strftime("%m"))), fechafin_semana.strftime("%Y") )
                        titulos_rep.append(fecha_letra) # 9-abr-2021 Jorge L.- aqui agrego a titulos las fechas de todos los domingos
                        total_recibidos     = 0
                        total_atendidas     = 0 
                        for j in range(len(fila_areas)-1): # 9-abr-2021 Jorge L.- se realiza el conteo de las areas menos la columna total
                            cantidad_recibidos  = 0
                            cantidad_atendidas  = 0                        
                            if fila_areas[j] == 'CMAS':
                                cantidad_recibidos = self.busqueda_count_catax(model_catax, fechaini_semana, fechafin_semana, [10])
                                cantidad_atendidas = self.busqueda_count_catax(model_catax, fechaini_semana, fechafin_semana, [10], ['ATEN'], atendidas=True)
                                total_aten_cmas += cantidad_atendidas
                                total_reci_cmas += cantidad_recibidos
                            elif fila_areas[j] == 'Gestión de Energía':
                                cantidad_recibidos = self.busqueda_count_catax(model_catax, fechaini_semana, fechafin_semana, [3])
                                cantidad_atendidas = self.busqueda_count_catax(model_catax, fechaini_semana, fechafin_semana, [3], ['ATEN'], atendidas=True)
                                total_aten_ge += cantidad_atendidas
                                total_reci_ge += cantidad_recibidos
                            elif fila_areas[j] == 'Obras Públicas':
                                cantidad_recibidos = self.busqueda_count_catax(model_catax, fechaini_semana, fechafin_semana, [4])
                                cantidad_atendidas = self.busqueda_count_catax(model_catax, fechaini_semana, fechafin_semana, [4], ['ATEN'], atendidas=True)
                                total_aten_op += cantidad_atendidas
                                total_reci_op += cantidad_recibidos
                            elif fila_areas[j] == 'Recursos Naturales y Cambio Climático':
                                cantidad_recibidos = self.busqueda_count_catax(model_catax, fechaini_semana, fechafin_semana, [5, 7, 8, 11])
                                cantidad_atendidas = self.busqueda_count_catax(model_catax, fechaini_semana, fechafin_semana, [5, 7, 8, 11], ['ATEN'], atendidas=True)
                                total_aten_rc += cantidad_atendidas
                                total_reci_rc += cantidad_recibidos
                            elif fila_areas[j] == 'Supervisión y Protección Ambiental':
                                cantidad_recibidos = self.busqueda_count_catax(model_catax, fechaini_semana, fechafin_semana, [12]) 
                                cantidad_atendidas = self.busqueda_count_catax(model_catax, fechaini_semana, fechafin_semana, [12], ['ATEN'], atendidas=True)                                                                               
                                total_aten_spa += cantidad_atendidas
                                total_reci_spa += cantidad_recibidos
                            elif fila_areas[j] == 'Gestión Integral de Residuos Sólidos':
                                cantidad_recibidos = self.busqueda_count_catax(model_catax, fechaini_semana, fechafin_semana, [6])
                                cantidad_atendidas = self.busqueda_count_catax(model_catax, fechaini_semana, fechafin_semana, [6], ['ATEN'], atendidas=True)
                                total_aten_gesti += cantidad_atendidas
                                total_reci_gesti += cantidad_recibidos
                            elif fila_areas[j] == 'Atención Ciudadana':
                                cantidad_recibidos = self.busqueda_count_catax(model_catax, fechaini_semana, fechafin_semana, [9])                            
                                cantidad_atendidas = self.busqueda_count_catax(model_catax, fechaini_semana, fechafin_semana, [9], ['ATEN'], atendidas=True)
                                total_aten_atenc += cantidad_atendidas
                                total_reci_atenc += cantidad_recibidos
                            elif fila_areas[j] == 'SIPINNA':
                                cantidad_recibidos = self.busqueda_count_catax(model_catax, fechaini_semana, fechafin_semana, [13])                            
                                cantidad_atendidas = self.busqueda_count_catax(model_catax, fechaini_semana, fechafin_semana, [13], ['ATEN'], atendidas=True)
                                total_aten_sipinna += cantidad_atendidas
                                total_reci_sipinna += cantidad_recibidos
                            elif fila_areas[j] == 'Desarrollo urbano':
                                cantidad_recibidos = self.busqueda_count_catax(model_catax, fechaini_semana, fechafin_semana, [14,15])                            
                                cantidad_atendidas = self.busqueda_count_catax(model_catax, fechaini_semana, fechafin_semana, [14,15], ['ATEN'], atendidas=True)
                                total_aten_du += cantidad_atendidas
                                total_reci_du += cantidad_recibidos
                            elif fila_areas[j] == 'DIF Municipal':
                                cantidad_recibidos = self.busqueda_count_catax(model_catax, fechaini_semana, fechafin_semana, [16])                            
                                cantidad_atendidas = self.busqueda_count_catax(model_catax, fechaini_semana, fechafin_semana, [16], ['ATEN'], atendidas=True)
                                total_aten_dm += cantidad_atendidas
                                total_reci_dm += cantidad_recibidos
                            elif fila_areas[j] == 'Comercio':
                                cantidad_recibidos = self.busqueda_count_catax(model_catax, fechaini_semana, fechafin_semana, [17,18,19])                            
                                cantidad_atendidas = self.busqueda_count_catax(model_catax, fechaini_semana, fechafin_semana, [17,18,19], ['ATEN'], atendidas=True)
                                total_aten_mc += cantidad_atendidas
                                total_reci_mc += cantidad_recibidos
                            elif fila_areas[j] == 'Protección civil':
                                cantidad_recibidos = self.busqueda_count_catax(model_catax, fechaini_semana, fechafin_semana, [20])                            
                                cantidad_atendidas = self.busqueda_count_catax(model_catax, fechaini_semana, fechafin_semana, [20], ['ATEN'], atendidas=True)
                                total_aten_pc += cantidad_atendidas
                                total_reci_pc += cantidad_recibidos
                            elif fila_areas[j] == 'Recaudación':
                                cantidad_recibidos = self.busqueda_count_catax(model_catax, fechaini_semana, fechafin_semana, [21])                            
                                cantidad_atendidas = self.busqueda_count_catax(model_catax, fechaini_semana, fechafin_semana, [21], ['ATEN'], atendidas=True)
                                total_aten_cm += cantidad_atendidas
                                total_reci_cm += cantidad_recibidos
                            elif fila_areas[j] == 'Registro civil':
                                cantidad_recibidos = self.busqueda_count_catax(model_catax, fechaini_semana, fechafin_semana, [22])                            
                                cantidad_atendidas = self.busqueda_count_catax(model_catax, fechaini_semana, fechafin_semana, [22], ['ATEN'], atendidas=True)
                                total_aten_reg_civ += cantidad_atendidas
                                total_reci_reg_civ += cantidad_recibidos
                            elif fila_areas[j] == 'Seguridad Ciudadana y Tránsito Municipal':
                                cantidad_recibidos = self.busqueda_count_catax(model_catax, fechaini_semana, fechafin_semana, [23])                            
                                cantidad_atendidas = self.busqueda_count_catax(model_catax, fechaini_semana, fechafin_semana, [23], ['ATEN'], atendidas=True)
                                total_aten_segu += cantidad_atendidas
                                total_reci_segu += cantidad_recibidos
                                

                            total_recibidos = total_recibidos + cantidad_recibidos # 9-abr-2021 Jorge L.- lleva el conteo de los valores por semana
                            total_atendidas  = total_atendidas  + cantidad_atendidas    # 9-abr-2021 Jorge L.-                                                    

                            #imprime cantidad por semana
                            ws.write(inicio_datos_fila + j, no_columna_ocupada+1, cantidad_recibidos, style=style_resultados)  # 9-abr-2021 Jorge L.- Se imprime la cantidad de registros atendidos por semana, para calcular la posicion de la fila se toma el inicio de datos mas la cantidad de areas que existen y la columna el auto incremental de columna ocupada mas 2 para las recibidas 
                            ws.write(inicio_datos_fila + j, no_columna_ocupada+2, cantidad_atendidas, style=style_resultados) # 9-abr-2021 Jorge L.- Se imprime la cantidad de registros atendidos por semana, para calcular la posicion de la fila se toma el inicio de datos mas la cantidad de areas que existen y la columna el auto incremental de columna ocupada mas 2 para las atendidas
                            ws.col(inicio_datos_fila+j).width = 3000                                                 
                    
                        #imprime totales
                        ws.write(len(fila_areas)+inicio_datos_fila-1, no_columna_ocupada+1, total_recibidos, style=style_totales)  # 9-abr-2021 Jorge L.- Se genera la columna totales, para calcular la fila se toma el inicio de datos de fila mas el numero de areas menos el total para posicionar en la fila, para la columna el incremental de columna ocupada mas 1 para las recibidas
                        ws.write(len(fila_areas)+inicio_datos_fila-1, no_columna_ocupada+2, total_atendidas, style=style_totales)  # 9-abr-2021 Jorge L.- Se genera la columna totales, para calcular la fila se toma el inicio de datos de fila mas el numero de areas menos el total para posicionar en la fila, para la columna el incremental de columna ocupada mas 2 para las pendientes
                        no_columna_ocupada += 2  # 9-abr-2021 Jorge L.- se auto incremente en 2 por las dos columnas que se calculan que son recibidas y atendidas por semana                                   

                    estatus = ['R', 'enproceso'] # 9-abr-2021 Jorge L.- variable donde obtiene el filtro de pendientes
                    total_pendientes = 0
                    for k in range(len(fila_areas)-1): # 9-abr-2021 Jorge L.-  este ciclo exclusivo para imprimir columna final donde contiene el conteo de todos los casis pendientes hasta la actualidad
                        cantidad_pendientes = 0
                        if fila_areas[k] == 'CMAS':
                            if self.reporte_oficial != 'I':
                                cantidad_pendientes = total_reci_cmas - total_aten_cmas
                            else:
                                cantidad_pendientes = model_catax.sudo().search_count([('create_date','>=', fecha_inicio.strftime("%Y-%m-%d")),('create_date', '<=', fechafin_semana.strftime("%Y-%m-%d") ),('categoria', 'in', [10]),('estatus', 'in', estatus)])
                        elif fila_areas[k] == 'Gestión de Energía':
                            if self.reporte_oficial != 'I':
                                cantidad_pendientes = total_reci_ge - total_aten_ge
                            else:                            
                                cantidad_pendientes = model_catax.sudo().search_count([('create_date','>=', fecha_inicio.strftime("%Y-%m-%d")),('create_date', '<=', fechafin_semana.strftime("%Y-%m-%d") ),('categoria', 'in', [3]),('estatus', 'in', estatus)])
                        elif fila_areas[k] == 'Obras Públicas':
                            if self.reporte_oficial != 'I':
                                cantidad_pendientes = total_reci_op - total_aten_op
                            else:                            
                                cantidad_pendientes = model_catax.sudo().search_count([('create_date','>=', fecha_inicio.strftime("%Y-%m-%d")),('create_date', '<=', fechafin_semana.strftime("%Y-%m-%d") ),('categoria', 'in', [4]),('estatus', 'in', estatus)])
                        elif fila_areas[k] == 'Recursos Naturales y Cambio Climático':
                            if self.reporte_oficial != 'I':
                                cantidad_pendientes = total_reci_rc - total_aten_rc
                            else:                            
                                cantidad_pendientes = model_catax.sudo().search_count([('create_date','>=', fecha_inicio.strftime("%Y-%m-%d")),('create_date', '<=', fechafin_semana.strftime("%Y-%m-%d") ),('categoria', 'in', [5, 7, 8, 11]),('estatus', 'in', estatus)])
                        elif fila_areas[k] == 'Supervisión y Protección Ambiental':
                            if self.reporte_oficial != 'I':
                                cantidad_pendientes = total_reci_spa - total_aten_spa
                            else:                            
                                cantidad_pendientes = model_catax.sudo().search_count([('create_date','>=', fecha_inicio.strftime("%Y-%m-%d")),('create_date', '<=', fechafin_semana.strftime("%Y-%m-%d") ),('categoria', 'in', [12]),('estatus', 'in', estatus)])                        
                        elif fila_areas[k] == 'Gestión Integral de Residuos Sólidos':
                            if self.reporte_oficial != 'I':
                                cantidad_pendientes = total_reci_gesti - total_aten_gesti
                            else:                            
                                cantidad_pendientes = model_catax.sudo().search_count([('create_date','>=', fecha_inicio.strftime("%Y-%m-%d")),('create_date', '<=', fechafin_semana.strftime("%Y-%m-%d") ),('categoria', 'in', [6]),('estatus', 'in', estatus)])
                        elif fila_areas[k] == 'Atención Ciudadana':
                            if self.reporte_oficial != 'I':
                                cantidad_pendientes = total_reci_atenc - total_aten_atenc
                            else:                            
                                cantidad_pendientes = model_catax.sudo().search_count([('create_date','>=', fecha_inicio.strftime("%Y-%m-%d")),('create_date', '<=', fechafin_semana.strftime("%Y-%m-%d") ),('categoria', 'in', [9]),('estatus', 'in', estatus)])

                        elif fila_areas[k] == 'SIPINNA':
                            if self.reporte_oficial != 'I':
                                cantidad_pendientes = total_reci_sipinna - total_aten_sipinna
                            else:                            
                                cantidad_pendientes = model_catax.sudo().search_count([('create_date','>=', fecha_inicio.strftime("%Y-%m-%d")),('create_date', '<=', fechafin_semana.strftime("%Y-%m-%d") ),('categoria', 'in', [13]),('estatus', 'in', estatus)])

                        elif fila_areas[k] == 'Desarrollo urbano':
                            if self.reporte_oficial != 'I':
                                cantidad_pendientes = total_reci_du - total_aten_du
                            else:                            
                                cantidad_pendientes = model_catax.sudo().search_count([('create_date','>=', fecha_inicio.strftime("%Y-%m-%d")),('create_date', '<=', fechafin_semana.strftime("%Y-%m-%d") ),('categoria', 'in', [14,15]),('estatus', 'in', estatus)])

                        elif fila_areas[k] == 'DIF Municipal':
                            if self.reporte_oficial != 'I':
                                cantidad_pendientes = total_reci_dm - total_aten_dm
                            else:                            
                                cantidad_pendientes = model_catax.sudo().search_count([('create_date','>=', fecha_inicio.strftime("%Y-%m-%d")),('create_date', '<=', fechafin_semana.strftime("%Y-%m-%d") ),('categoria', 'in', [16]),('estatus', 'in', estatus)])

                        elif fila_areas[k] == 'Comercio':
                            if self.reporte_oficial != 'I':
                                cantidad_pendientes = total_reci_mc - total_aten_mc
                            else:                            
                                cantidad_pendientes = model_catax.sudo().search_count([('create_date','>=', fecha_inicio.strftime("%Y-%m-%d")),('create_date', '<=', fechafin_semana.strftime("%Y-%m-%d") ),('categoria', 'in', [17,18,19]),('estatus', 'in', estatus)])

                        elif fila_areas[k] == 'Protección civil':
                            if self.reporte_oficial != 'I':
                                cantidad_pendientes = total_reci_pc - total_aten_pc
                            else:                            
                                cantidad_pendientes = model_catax.sudo().search_count([('create_date','>=', fecha_inicio.strftime("%Y-%m-%d")),('create_date', '<=', fechafin_semana.strftime("%Y-%m-%d") ),('categoria', 'in', [20]),('estatus', 'in', estatus)])

                        elif fila_areas[k] == 'Recaudación':
                            if self.reporte_oficial != 'I':
                                cantidad_pendientes = total_reci_cm - total_aten_cm
                            else:                            
                                cantidad_pendientes = model_catax.sudo().search_count([('create_date','>=', fecha_inicio.strftime("%Y-%m-%d")),('create_date', '<=', fechafin_semana.strftime("%Y-%m-%d") ),('categoria', 'in', [21]),('estatus', 'in', estatus)])

                        elif fila_areas[k] == 'Registro civil':
                            if self.reporte_oficial != 'I':
                                cantidad_pendientes = total_reci_reg_civ - total_aten_reg_civ
                            else:                            
                                cantidad_pendientes = model_catax.sudo().search_count([('create_date','>=', fecha_inicio.strftime("%Y-%m-%d")),('create_date', '<=', fechafin_semana.strftime("%Y-%m-%d") ),('categoria', 'in', [22]),('estatus', 'in', estatus)])

                        elif fila_areas[k] == 'Seguridad Ciudadana y Tránsito Municipal':
                            if self.reporte_oficial != 'I':
                                cantidad_pendientes = total_reci_segu - total_aten_segu
                            else:                            
                                cantidad_pendientes = model_catax.sudo().search_count([('create_date','>=', fecha_inicio.strftime("%Y-%m-%d")),('create_date', '<=', fechafin_semana.strftime("%Y-%m-%d") ),('categoria', 'in', [23]),('estatus', 'in', estatus)])


                        total_pendientes = total_pendientes + cantidad_pendientes
                        ws.write(inicio_datos_fila + k, no_columna_ocupada+1, cantidad_pendientes, style=style_resultados) # 9-abr-2021 Jorge L.-  imprime por fila los casos pendientes por areas

                    ws.write(len(fila_areas)+inicio_datos_fila-1, no_columna_ocupada+1, total_pendientes, style=style_totales)  # 9-abr-2021 Jorge L.-  imprime la columna de total casos pendientes

                titulos_rep.append('Casos pendientes ')            

                self.genera_titulos(ws ,titulos_rep, style_cabecera)   
            elif self.tipo_reporte == 'T':
                inicio_datos_fila = 3
                if not self.fecha_ini or not self.fecha_fin:                    
                    raise exceptions.Warning("Imposible generar informe debera asignar el rango de fechas.")
                if not  self.validate_daterange(self.fecha_ini, self.fecha_fin):
                    raise exceptions.Warning("La fecha inicial es mayor a la fecha final.")                    
                cont = 0
                titulos_rep = [ 'Área', 'Reportes atendidos', 'Encuestas enviadas', 'Encuestas contestadas', 'Resultado promedio de la calidad de atención', 'Resultado promedio de resolución de reporte' ]
                ws.write_merge(0, 0, 0, 5, 'CATAX – Encuesta de satisfacción',style=style_cabecera)
                for x in titulos_rep:                    
                    ws.write_merge(2, 2, cont , cont, x, style=style_cabecera)
                    ws.row(cont).height_mismatch = True
                    ws.row(cont).height = 900
                    ws.col(cont).width = 3000
                    cont+= 1
                
                cont = 0
                for y in fila_areas:
                    if y == 'TOTAL':
                        ws.write(inicio_datos_fila+cont, 0,y, style=style_totales) # 9-abr-2021 Jorge L.- imprimo valor
                    else:
                        ws.write(inicio_datos_fila+cont, 0,y, style=style_resultados)
                    
                    ws.row(inicio_datos_fila+cont).height_mismatch = True 
                    ws.row(inicio_datos_fila+cont).height = 500    
                    ws.col(0).width = 8000
                    ws.col(cont).width = 5000 
                    cont+= 1

                total_rencuestas_env  = 0
                total_atendidas       = 0
                total_encuestas_calif = 0
                total_prom_aten       = 0
                total_prom_rep        = 0

                fecha_fin= datetime.strptime(self.fecha_fin, '%Y-%m-%d').date() 
                fecha_ini = datetime.strptime(self.fecha_ini, '%Y-%m-%d').date() 
                no_columna_ocupada = 0
                fecha_letra_ini = '%s-%s-%s' % (fecha_ini.strftime("%d"),self.month_converter(int(fecha_ini.strftime("%m"))), fecha_ini.strftime("%Y") )
                fecha_letra_fin = '%s-%s-%s' % (fecha_fin.strftime("%d"),self.month_converter(int(fecha_fin.strftime("%m"))), fecha_fin.strftime("%Y") )
                rango_fecha     = fecha_letra_ini +' al ' + fecha_letra_fin
                ws.write_merge(1, 1, 0, 5, 'Periodo: '+rango_fecha ,style=style_cabecera)
                for j in range(len(fila_areas)-1): # 9-abr-2021 Jorge L.- se realiza el conteo de las areas menos la columna total
                    cantidad_repvalorado = 0
                    cantidad_atendidas   = 0 
                    cant_reg             = 0    
                    sum_calif_aten       = 0
                    sum_calif_val        = 0   
                    promedio_atencion    = 0
                    promedio_valor       = 0                                
                    if fila_areas[j] == 'CMAS':
                        cantidad_repvalorado = model_catax.sudo().search_count([('fecha_finalizada','>=', fecha_ini),('fecha_finalizada', '<=', fecha_fin),('categoria', 'in', [10]),('estatus', 'in', ['ATEN']),('encuesta_enviada','=', True)])
                        cantidad_atendidas = self.busqueda_count_catax(model_catax, fecha_ini, fecha_fin, [10], ['ATEN'], atendidas=True)                        
                        reg_calif_reporte  = model_catax.sudo().search([('fecha_finalizada','>=', fecha_ini),('fecha_finalizada', '<=', fecha_fin),('categoria', 'in', [10]),('eval_calif','=', True)])
                        cant_reg =  len(reg_calif_reporte)

                    elif fila_areas[j] == 'Gestión de Energía':
                        cantidad_repvalorado = model_catax.sudo().search_count([('fecha_finalizada','>=', fecha_ini),('fecha_finalizada', '<=', fecha_fin),('categoria', 'in', [3]),('estatus', 'in', ['ATEN']),('encuesta_enviada','=', True)])
                        cantidad_atendidas = self.busqueda_count_catax(model_catax, fecha_ini, fecha_fin, [3], ['ATEN'], atendidas=True)                        
                        reg_calif_reporte  = model_catax.sudo().search([('fecha_finalizada','>=', fecha_ini),('fecha_finalizada', '<=', fecha_fin),('categoria', 'in', [3]),('eval_calif','=', True)])
                        cant_reg =  len(reg_calif_reporte)

                    elif fila_areas[j] == 'Obras Públicas':
                        cantidad_repvalorado = model_catax.sudo().search_count([('fecha_finalizada','>=', fecha_ini),('fecha_finalizada', '<=', fecha_fin),('categoria', 'in', [4]),('estatus', 'in', ['ATEN']),('encuesta_enviada','=', True)])
                        cantidad_atendidas = self.busqueda_count_catax(model_catax, fecha_ini, fecha_fin, [4], ['ATEN'], atendidas=True)                        
                        reg_calif_reporte  = model_catax.sudo().search([('fecha_finalizada','>=', fecha_ini),('fecha_finalizada', '<=', fecha_fin),('categoria', 'in', [4]),('eval_calif','=', True)])
                        cant_reg =  len(reg_calif_reporte)                        

                    elif fila_areas[j] == 'Recursos Naturales y Cambio Climático':
                        cantidad_repvalorado = model_catax.sudo().search_count([('fecha_finalizada','>=', fecha_ini),('fecha_finalizada', '<=', fecha_fin),('categoria', 'in', [5, 7, 8, 11]),('estatus', 'in', ['ATEN']),('encuesta_enviada','=', True)])
                        cantidad_atendidas = self.busqueda_count_catax(model_catax, fecha_ini, fecha_fin, [5, 7, 8, 11], ['ATEN'], atendidas=True)                        
                        reg_calif_reporte  = model_catax.sudo().search([('fecha_finalizada','>=', fecha_ini),('fecha_finalizada', '<=', fecha_fin),('categoria', 'in', [5, 7, 8, 11]),('eval_calif','=', True)])
                        cant_reg =  len(reg_calif_reporte)  
                                                
                    elif fila_areas[j] == 'Supervisión y Protección Ambiental':
                        cantidad_repvalorado = model_catax.sudo().search_count([('fecha_finalizada','>=', fecha_ini),('fecha_finalizada', '<=', fecha_fin),('categoria', 'in', [12]),('estatus', 'in', ['ATEN']),('encuesta_enviada','=', True)])
                        cantidad_atendidas = self.busqueda_count_catax(model_catax, fecha_ini, fecha_fin, [12], ['ATEN'], atendidas=True)                        
                        reg_calif_reporte  = model_catax.sudo().search([('fecha_finalizada','>=', fecha_ini),('fecha_finalizada', '<=', fecha_fin),('categoria', 'in', [12]),('eval_calif','=', True)])
                        cant_reg =  len(reg_calif_reporte)   

                    elif fila_areas[j] == 'Gestión Integral de Residuos Sólidos':
                        cantidad_repvalorado = model_catax.sudo().search_count([('fecha_finalizada','>=', fecha_ini),('fecha_finalizada', '<=', fecha_fin),('categoria', 'in', [6]),('estatus', 'in', ['ATEN']),('encuesta_enviada','=', True)])
                        cantidad_atendidas = self.busqueda_count_catax(model_catax, fecha_ini, fecha_fin, [6], ['ATEN'], atendidas=True)                        
                        reg_calif_reporte  = model_catax.sudo().search([('fecha_finalizada','>=', fecha_ini),('fecha_finalizada', '<=', fecha_fin),('categoria', 'in', [6]),('eval_calif','=', True)])
                        cant_reg =  len(reg_calif_reporte)   

                    elif fila_areas[j] == 'Atención Ciudadana':
                        cantidad_repvalorado = model_catax.sudo().search_count([('fecha_finalizada','>=', fecha_ini),('fecha_finalizada', '<=', fecha_fin),('categoria', 'in', [9]),('estatus', 'in', ['ATEN']),('encuesta_enviada','=', True)])
                        cantidad_atendidas = self.busqueda_count_catax(model_catax, fecha_ini, fecha_fin, [9], ['ATEN'], atendidas=True)                        
                        reg_calif_reporte  = model_catax.sudo().search([('fecha_finalizada','>=', fecha_ini),('fecha_finalizada', '<=', fecha_fin),('categoria', 'in', [9]),('eval_calif','=', True)])
                        cant_reg =  len(reg_calif_reporte)  

                    elif fila_areas[j] == 'SIPINNA':
                        cantidad_repvalorado = model_catax.sudo().search_count([('fecha_finalizada','>=', fecha_ini),('fecha_finalizada', '<=', fecha_fin),('categoria', 'in', [13]),('estatus', 'in', ['ATEN']),('encuesta_enviada','=', True)])
                        cantidad_atendidas = self.busqueda_count_catax(model_catax, fecha_ini, fecha_fin, [13], ['ATEN'], atendidas=True)                        
                        reg_calif_reporte  = model_catax.sudo().search([('fecha_finalizada','>=', fecha_ini),('fecha_finalizada', '<=', fecha_fin),('categoria', 'in', [13]),('eval_calif','=', True)])
                        cant_reg =  len(reg_calif_reporte)  

                    elif fila_areas[j] == 'Desarrollo urbano':
                        cantidad_repvalorado = model_catax.sudo().search_count([('fecha_finalizada','>=', fecha_ini),('fecha_finalizada', '<=', fecha_fin),('categoria', 'in', [14,15]),('estatus', 'in', ['ATEN']),('encuesta_enviada','=', True)])
                        cantidad_atendidas = self.busqueda_count_catax(model_catax, fecha_ini, fecha_fin, [14,15], ['ATEN'], atendidas=True)                        
                        reg_calif_reporte  = model_catax.sudo().search([('fecha_finalizada','>=', fecha_ini),('fecha_finalizada', '<=', fecha_fin),('categoria', 'in', [14,15]),('eval_calif','=', True)])
                        cant_reg =  len(reg_calif_reporte)  

                    elif fila_areas[j] == 'DIF Municipal':
                        cantidad_repvalorado = model_catax.sudo().search_count([('fecha_finalizada','>=', fecha_ini),('fecha_finalizada', '<=', fecha_fin),('categoria', 'in', [16]),('estatus', 'in', ['ATEN']),('encuesta_enviada','=', True)])
                        cantidad_atendidas = self.busqueda_count_catax(model_catax, fecha_ini, fecha_fin, [16], ['ATEN'], atendidas=True)                        
                        reg_calif_reporte  = model_catax.sudo().search([('fecha_finalizada','>=', fecha_ini),('fecha_finalizada', '<=', fecha_fin),('categoria', 'in', [16]),('eval_calif','=', True)])
                        cant_reg =  len(reg_calif_reporte)  

                    elif fila_areas[j] == 'Comercio':
                        cantidad_repvalorado = model_catax.sudo().search_count([('fecha_finalizada','>=', fecha_ini),('fecha_finalizada', '<=', fecha_fin),('categoria', 'in', [17,18,19]),('estatus', 'in', ['ATEN']),('encuesta_enviada','=', True)])
                        cantidad_atendidas = self.busqueda_count_catax(model_catax, fecha_ini, fecha_fin, [17,18,19], ['ATEN'], atendidas=True)                        
                        reg_calif_reporte  = model_catax.sudo().search([('fecha_finalizada','>=', fecha_ini),('fecha_finalizada', '<=', fecha_fin),('categoria', 'in', [17,18,19]),('eval_calif','=', True)])
                        cant_reg =  len(reg_calif_reporte)  

                    elif fila_areas[j] == 'Protección civil':
                        cantidad_repvalorado = model_catax.sudo().search_count([('fecha_finalizada','>=', fecha_ini),('fecha_finalizada', '<=', fecha_fin),('categoria', 'in', [20]),('estatus', 'in', ['ATEN']),('encuesta_enviada','=', True)])
                        cantidad_atendidas = self.busqueda_count_catax(model_catax, fecha_ini, fecha_fin, [20], ['ATEN'], atendidas=True)                        
                        reg_calif_reporte  = model_catax.sudo().search([('fecha_finalizada','>=', fecha_ini),('fecha_finalizada', '<=', fecha_fin),('categoria', 'in', [20]),('eval_calif','=', True)])
                        cant_reg =  len(reg_calif_reporte)  

                    elif fila_areas[j] == 'Recaudación':
                        cantidad_repvalorado = model_catax.sudo().search_count([('fecha_finalizada','>=', fecha_ini),('fecha_finalizada', '<=', fecha_fin),('categoria', 'in', [21]),('estatus', 'in', ['ATEN']),('encuesta_enviada','=', True)])
                        cantidad_atendidas = self.busqueda_count_catax(model_catax, fecha_ini, fecha_fin, [21], ['ATEN'], atendidas=True)                        
                        reg_calif_reporte  = model_catax.sudo().search([('fecha_finalizada','>=', fecha_ini),('fecha_finalizada', '<=', fecha_fin),('categoria', 'in', [21]),('eval_calif','=', True)])
                        cant_reg =  len(reg_calif_reporte)  

                    elif fila_areas[j] == 'Registro civil':
                        cantidad_repvalorado = model_catax.sudo().search_count([('fecha_finalizada','>=', fecha_ini),('fecha_finalizada', '<=', fecha_fin),('categoria', 'in', [22]),('estatus', 'in', ['ATEN']),('encuesta_enviada','=', True)])
                        cantidad_atendidas = self.busqueda_count_catax(model_catax, fecha_ini, fecha_fin, [22], ['ATEN'], atendidas=True)                        
                        reg_calif_reporte  = model_catax.sudo().search([('fecha_finalizada','>=', fecha_ini),('fecha_finalizada', '<=', fecha_fin),('categoria', 'in', [22]),('eval_calif','=', True)])
                        cant_reg =  len(reg_calif_reporte)  

                    elif fila_areas[j] == 'Seguridad Ciudadana y Tránsito Municipal':
                        cantidad_repvalorado = model_catax.sudo().search_count([('fecha_finalizada','>=', fecha_ini),('fecha_finalizada', '<=', fecha_fin),('categoria', 'in', [23]),('estatus', 'in', ['ATEN']),('encuesta_enviada','=', True)])
                        cantidad_atendidas = self.busqueda_count_catax(model_catax, fecha_ini, fecha_fin, [23], ['ATEN'], atendidas=True)                        
                        reg_calif_reporte  = model_catax.sudo().search([('fecha_finalizada','>=', fecha_ini),('fecha_finalizada', '<=', fecha_fin),('categoria', 'in', [23]),('eval_calif','=', True)])
                        cant_reg =  len(reg_calif_reporte)  

                        

                    if reg_calif_reporte:
                        for reg in reg_calif_reporte:
                            aux_reg = model_catax.sudo().search([('id', '=', reg.id)])
                            sum_calif_aten = sum_calif_aten + int(aux_reg['calificacion_atencion'])
                            sum_calif_val  = sum_calif_val  + int(aux_reg['calificacion_reporte'])

                    if cant_reg == 0:
                        promedio_atencion = 0
                        promedio_valor    = 0
                    else: 
                        promedio_atencion = (sum_calif_aten / cant_reg) *2
                        promedio_valor    = (sum_calif_val / cant_reg) *2

                    total_atendidas       += cantidad_atendidas
                    total_rencuestas_env  += cantidad_repvalorado
                    total_encuestas_calif += cant_reg
                    total_prom_aten       += round(promedio_atencion,1)
                    total_prom_rep        += round(promedio_valor,1)                    
                    
                    ws.write(inicio_datos_fila + j, no_columna_ocupada+1, cantidad_atendidas,          style=style_resultados)   # 'Atendidos'
                    ws.write(inicio_datos_fila + j, no_columna_ocupada+2, cantidad_repvalorado,        style=style_resultados)   # 'Encuestas enviadas'
                    ws.write(inicio_datos_fila + j, no_columna_ocupada+3, cant_reg,                    style=style_resultados)   # 'Encuestas contestadas' 
                    ws.write(inicio_datos_fila + j, no_columna_ocupada+4, round(promedio_atencion,1),    style=style_resultados)   # 'Resultado en calidad de atención' 
                    ws.write(inicio_datos_fila + j, no_columna_ocupada+5, round(promedio_valor,1),       style=style_resultados)   # 'Resultado en resolución de reporte' 


                #totales (ultima fila)  
                
                cant_areas = len(fila_areas)-1
                catax_prom_aten =  total_prom_aten / cant_areas
                catax_prom_rep  =  total_prom_rep / cant_areas

                ws.write(cant_areas +inicio_datos_fila , 1, total_atendidas,        style=style_totales)   # 'Atendidos'
                ws.write(cant_areas +inicio_datos_fila , 2, total_rencuestas_env,   style=style_totales)   # 'Encuestas enviadas'
                ws.write(cant_areas +inicio_datos_fila , 3, total_encuestas_calif,  style=style_totales)   # 'Encuestas contestadas' 
                ws.write(cant_areas +inicio_datos_fila , 4, round(catax_prom_aten,1), style=style_totales)   # 'Resultado en calidad de atención' 
                ws.write(cant_areas +inicio_datos_fila , 5, round(catax_prom_rep,1),  style=style_totales)   # 'Resultado en resolución de reporte' 


            wb.save(template_path + '/' + file_output_name)

            return {
                'type': 'ir.actions.act_url',
                'url': '/catax/download_file?path=%s&file_name=%s' % (output_template_path, file_output_name),
                'target': 'new',
            }

class reporte_individual(models.AbstractModel):
    _name = "report.catax.reporte_individual_template"
    _description = "Agrega valores al pdf"

    @api.model
    def get_report_values(self, docids, data=None):
        docs = self.env['catax.catax'].browse(docids[0])
        url_mapa_image = "https://maps.googleapis.com/maps/api/staticmap?center="+docs.latitud+","+docs.longitud+"&zoom=15&size=300x300&markers=color:blue%7Clabel:R%7C"+docs.latitud+","+docs.longitud+"&key=AIzaSyDt4wgXTrf0mLrmn6WA3SceXEBBkkS5glY"
        try:
            url_mapa = requests.get(url_mapa_image)
            url_mapa = base64.b64encode(url_mapa.content)
        except ValueError as er:
            logger.info(er)
            url_mapa = ""
        
        array_return = {
            'doc_model': 'res.partner',
            'data': data,
            'docs': docs,
            'url_mapa': url_mapa,
        }
        return array_return