#!/usr/bin/python3
# # -*- coding: utf-8 -*-
"""
/***************************************************************************
Name                 : MapBiomas Alert
Description          : Class for work with MapBiomas Alert
Date                 : April, 2019
copyright            : (C) 2019 by Luiz Motta
email                : motta.luiz@gmail.com

 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from ast import Raise
import urllib.parse

import json, binascii, os, csv
from .accesssite import AccessSite
from qgis.PyQt.QtCore import (
    QObject, QUrl,
    pyqtSlot, pyqtSignal
)
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis.PyQt.QtGui import QPixmap

from qgis.core import (
    Qgis, QgsProject, QgsApplication,
    QgsVectorLayer, QgsFeature, QgsGeometry,
    QgsFeatureRequest,
    QgsCoordinateReferenceSystem, QgsCoordinateTransform,
    QgsBlockingNetworkRequest,
    QgsTask,QgsVectorLayer, QgsDataSourceUri
)
from qgis import utils as QgsUtils


class Geometry_WKB():
    # Adaptation from https://github.com/elpaso/quickwkt/blob/master/QuickWKT.py
    SRID_FLAG = 0x20000000
    @staticmethod
    def decodeBinary(geom_hex):
        value = binascii.a2b_hex(geom_hex)
        value = value[::-1]
        value = binascii.b2a_hex(value)
        return value.decode("UTF-8")

    @staticmethod
    def encodeBinary(geom_hex):
            wkb = binascii.a2b_hex("{:08x}".format( geom_hex ) )
            wkb = wkb[::-1]
            wkb = binascii.b2a_hex(wkb)
            return wkb.decode("UTF-8")

    @staticmethod
    def getQgsGeometry_SRID(geom_hex):
        """ geomHex: ST_AsHexEWKB(geom) or ST_AsHexWKB(geom) """
        srid = None
        geomType = int("0x" + Geometry_WKB.decodeBinary(geom_hex[2:10]), 0)
        if geomType & Geometry_WKB.SRID_FLAG:
            srid = int("0x" + Geometry_WKB.decodeBinary(geom_hex[10:18]), 0)
            # String the srid from the wkb string
            geom_hex = geom_hex[:2] + Geometry_WKB.encodeBinary(geomType ^ Geometry_WKB.SRID_FLAG) + geom_hex[18:]

        geom = QgsGeometry()
        geom.fromWkb(binascii.a2b_hex(geom_hex))
        
        return ( geom, srid )


class API_MapbiomasAlert(QObject):

    urlGeoserver = 'https://geoserver.ecostage.com.br/geoserver/mapbiomas-alerta/wfs' #'https://geoserver.ecostage.com.br/geoserver/ows'
    urlReport = 'http://plataforma.alerta.mapbiomas.org/reports'
    access = AccessSite()
    fields = {
            'alert_code': {'definition': 'int(-1)'},
            'detected_at':  {'definition': 'string(10)'},
            'source': {'definition': 'string(100)'},
            #'dt_antes': {'definition': 'string(10)'},
            #'img_antes': {'definition': 'string(150)'},
            #'dt_depois': {'definition': 'string(10)'},
            #'img_depois': {'definition': 'string(150)'},
            'cars': {'definition': 'string(150)'},
            #'cars_qtd': {'definition': 'int(-1)'},
            'area_ha': {'definition': 'double'}
            }

    Q_TOKEN = """
    {
        "query": "mutation($email: String!, $password: String!)
            { 
                    signIn(email: $email, password: $password) { token }
            }",
        "variables": {
            "email": "_email_",
            "password": "_password_"
        }
    }
    """
    Q_ALLPUBLISHEDALERTS = """
    {
        "query": "
        query
        (
        $startDetectedAt: String
        $endDetectedAt: String
        $startPublishedAt: String
        $endPublishedAt: String
        $territoryIds: [Int!]
        $limit: Int
        $offset: Int
        )
        {
        publishedAlerts 
        (
            startDetectedAt: $startDetectedAt
            endDetectedAt: $endDetectedAt
            startPublishedAt: $startPublishedAt
            endPublishedAt: $endPublishedAt
            territoryIds: $territoryIds
            limit: $limit
            offset: $offset
        )
            { _fields_  }
        }",
        "variables": {
            "limit": _limit_, "offset": _offset_ ,
            "startDetectedAt": "_startDetectedAt_", 
            "endDetectedAt": "_endDetectedAt_",
            "startPublishedAt": "_startDetectedAt_",
            "endPublishedAt": "_endDetectedAt_",
            "territoryIds": [ _territoryIds_ ]
        }
    }
    """
    Q_IMAGES = """
    {
        "query": "
        query(
            $alertCode: Int!
        )
        {
        alertReport(alertCode: $alertCode )
        { images { before { url, satellite, acquiredAt } after  { url, satellite, acquiredAt } } }
        }",
        "variables": { "alertCode": _alertId_ }
    }
    """
    LIMIT = 50
    OFFSETID = 0;
    NETWORKREQUEST = QNetworkRequest(  QUrl('https://plataforma.alerta.mapbiomas.org/api/v1/graphql') )
    message = pyqtSignal(str, Qgis.MessageLevel)
    status = pyqtSignal(str)
    alerts = pyqtSignal(list)
    finishedAlert = pyqtSignal()
    images = pyqtSignal(dict)
    def __init__(self):
        super().__init__()
        self.taskManager = QgsApplication.taskManager()
        self.taskAlerts, self.taskImage = None, None
        self.request = QgsBlockingNetworkRequest()
        API_MapbiomasAlert.NETWORKREQUEST.setHeader( QNetworkRequest.ContentTypeHeader, 'application/json')
        self.tokenOk = False
        
        

    def _request(self, data):
        data = data.replace('\n', '').encode('utf-8')
        err = self.request.post( API_MapbiomasAlert.NETWORKREQUEST, data )
        if not err == QgsBlockingNetworkRequest.NoError:
            return None
        ba = self.request.reply().content() # QByteArray
        content = bytes( ba ).decode()
        return json.loads( content )

    def _replaceQuery(self, values, query):
        q = query
        for v in values.keys():
            q = q.replace( f"_{v}_", str( values[ v] ) )
        return q

    def setToken(self, email, password, sendMessage=False):
        values = { 'email': email, 'password': password }
        data = self._replaceQuery( values, self.Q_TOKEN )
        #print(data)
        response = self._request( data )
        if not response:
            self.message.emit( self.request.errorMessage(), Qgis.Critical )
            self.tokenOk = False
            return
        if not response['data']['signIn']:
            if sendMessage:
                self.message.emit( 'Invalid email or password', Qgis.Critical )
            self.tokenOk = False
            return
        token = response['data']['signIn']['token']
        value = f"Bearer {token}"
        API_MapbiomasAlert.NETWORKREQUEST.setRawHeader( b'Authorization', value.encode('utf-8') )
        self.tokenOk = True

    def getAlertsWFS(self, url, dbAlerts,fromDate, toDate,ids):
        def run(task):
            print('WFS mode')
            print('url= '+url)
            #uri = QgsDataSourceUri()
            #uri.setConnection("34.86.182.142", "5432", "alerta", "stg_geoserver_usr", "hJ2zZn0uW4af")
            #uri.setDataSource ("public", "temp_gis_published_alerts", 'geom')
            #layer= QgsVectorLayer (uri.uri(False), "temp_gis_published_alerts", "postgres")
            layer = QgsVectorLayer(url, 'qgis_published_alerts', 'WFS')
            #QgsProject.instance().addMapLayer(layer)
            for field in layer.fields():
                print(field.name(), field.typeName())
            #print('Here')
            values = layer.getFeatures()
            #print(values.next())
            values = [ dbAlerts.transformItemWFS( v ,self) for v in values ]
            self.alerts.emit( values )
            layer.reload()
            return { 'total': 1 }

        def finished(exception, dataResult=None):
            self.finishedAlert.emit()
            self.taskAlerts = None
            msg = f"Finished {dataResult['total']} alerts" if dataResult else ''
            self.status.emit( msg )

        task = QgsTask.fromFunction('Alert Task', run, on_finished=finished )
        task.setDependentLayers( [ dbAlerts.layer ] )
        self.taskAlerts = task
        self.taskManager.addTask( task )

    

    def getAlertsWFSnonThread(self, url, dbAlerts,fromDate, toDate,ids):
        print('WFS mode')
        print('url= '+url)
        #uri = QgsDataSourceUri()
        #uri.setConnection("34.86.182.142", "5432", "alerta", "stg_geoserver_usr", "hJ2zZn0uW4af")
        #uri.setDataSource ("public", "temp_gis_published_alerts", 'geom')
        #layer= QgsVectorLayer (uri.uri(False), "temp_gis_published_alerts", "postgres")
        layer = QgsVectorLayer(url, 'qgis_published_alerts', 'WFS')
        layer.setCustomProperty("showFeatureCount", True)
        #QgsProject.instance().addMapLayer(layer)
        for field in layer.fields():
            print(field.name(), field.typeName())
        #print('Here')
        values = layer.getFeatures()
        #print(values.next())
        values = [ dbAlerts.transformItemWFS( v ,self) for v in values ]
        self.alerts.emit( values )
        #layer.reload()
        return { 'total': 1 }

                #print(maxValue)
        #p = {
        #    'url': QUrl( url ),
        #}
        #self.access.requestUrl( p, self._addFeaturesLinkResponse, setFinished )

    def _addFeaturesLinkResponse(self, response):
        def getFeaturesResponse(data):
            def getGeometry(geometry):
                def getPolygonPoints(coordinates):
                    polylines = []
                    for line in coordinates:
                        polyline = [ QgsPointXY( p[0], p[1] ) for p in line ]
                        polylines.append( polyline )
                    return polylines

                if geometry['type'] == 'Polygon':
                    polygon = getPolygonPoints( geometry['coordinates'] )
                    return QgsGeometry.fromMultiPolygonXY( [ polygon ] )
                elif geometry['type'] == 'MultiPolygon':
                    polygons= []
                    for polygon in geometry['coordinates']:
                        polygons.append( getPolygonPoints( polygon ) )
                    return QgsGeometry.fromMultiPolygonXY( polygons )

                else:
                    None

            features = []
            for feat in data['features']:
                if self.access.isKill:
                    return features
                geom = getGeometry( feat['geometry'] )
                del feat['geometry']
                properties = feat['properties']
                item = {}
                for k in self.fields.keys():
                    item[ k ] = properties[ k ]
                if not item['cars'] is None:
                    item['cars'] = item['cars'].replace(';', '\n')
                else:
                    item['cars'] = ''
                item['geometry'] = geom
                features.append( item )
            return features

    @staticmethod
    def getUrlAlertsBySource(wktGeom,sourcename):
        params = {
            'service': 'WFS',
            'version': '1.0.0',
            'request': 'GetFeature',
            'typeName': 'mapbiomas-alerta:qgis_published_alerts',
            #'count':''+str(step),
            #'startIndex':''+str(page)
            #'outputFormat': 'application/json',
            #'MAXFEATURES':'5000'
            'cql_filter': "source ilike '%"+sourcename+"%'"
        }
        params = '&'.join( [ "{k}={v}".format( k=k, v=params[ k ] ) for k in params.keys() ] )
        return "{url}?{params}".format( url=API_MapbiomasAlert.urlGeoserver, params=params )
    

    @staticmethod
    def getUrlAlertsbyCQL(wktGeom,cql):
        params = {
            'service': 'WFS',
            'version': '1.0.0',
            'request': 'GetFeature',
            'typeName': 'mapbiomas-alerta:qgis_published_alerts',
            #'count':''+str(step),
            #'startIndex':''+str(page)
            #'outputFormat': 'application/json',
            #'MAXFEATURES':'5000'
            'cql_filter': cql
        }
        params = '&'.join( [ "{k}={v}".format( k=k, v=params[ k ] ) for k in params.keys() ] )
        return "{url}?{params}".format( url=API_MapbiomasAlert.urlGeoserver, params=params )
    
    @staticmethod
    def getUrlAlertsZero(wktGeom):
        params = {
            'service': 'WFS',
            'version': '1.0.0',
            'request': 'GetFeature',
            'typename': 'mapbiomas-alerta:qgis_published_alerts',
            #'count':''+str(step),
            #'startIndex':''+str(page)
            #'outputFormat': 'application/json',
            #'MAXFEATURES':'5000'
            'cql_filter': "id <= 20000"
        }
        params = '&'.join( [ "{k}={v}".format( k=k, v=params[ k ] ) for k in params.keys() ] )
        return "{url}?{params}".format( url=API_MapbiomasAlert.urlGeoserver, params=params )
    
    @staticmethod
    def getUrlAlertsPaginated(wktGeom,step,offset,after,before):
        params = {
            'service': 'WFS',
            'version': '1.0.0',
            'request': 'GetFeature',
            'typeName': 'mapbiomas-alerta:mv_qgis_published_alerts_snap_to_grid',
            'maxFeatures':''+str(step),
            'startIndex':''+str((offset*step)),
            'sortBy':'alert_code',
            #'outputFormat': 'application/json',
            #'MAXFEATURES':'10',
            'srs':'EPSG:4674',
            'srsName':'EPSG:4674',
            'cql_filter': 'detected_at between '+str(after)+' and '+str(before)
        }
        params = '&'.join( [ "{k}={v}".format( k=k, v=params[ k ] ) for k in params.keys() ] )
        return "{url}?{params}".format( url=API_MapbiomasAlert.urlGeoserver, params=params )

    @staticmethod
    def getUrlAlerts(wktGeom):
        params = {
            'service': 'WFS',
            'version': '1.0.0',
            'request': 'GetFeature',
            'typeName': 'mapbiomas-alerta:mv_qgis_published_alerts_snap_to_grid',
            #'count':''+str(step),
            #'startIndex':''+str(page)
            #'outputFormat': 'application/json',
            #'MAXFEATURES':'10'
            #'cql_filter': 'id >= 20000'
        }
        params = '&'.join( [ "{k}={v}".format( k=k, v=params[ k ] ) for k in params.keys() ] )
        return "{url}?{params}".format( url=API_MapbiomasAlert.urlGeoserver, params=params )


    def getAlerts(self, dbAlerts, startDetectedAt, endDetectedAt, territoryIds):
        def run(task):
            def request(values):
                maxValue = 0
                data = self._replaceQuery( values, self.Q_ALLPUBLISHEDALERTS )
                #print('Request DATA')
                #print(data)
                response = self._request( data )
                if not response:
                    msg = f"MapBiomas Alert: {self.request.errorMessage()}"
                    self.message.emit( msg, Qgis.Critical )
                    return -1
                if 'errors' in response:
                    l_messages = [ v['message'] for v in response['errors'] ]
                    msg = f"MapBiomas Alert: {','.join( l_messages )}"
                    self.message.emit( msg,  Qgis.Critical )
                    return -1
                values = response['data']['publishedAlerts']
                values = [ dbAlerts.transformItem( v ) for v in values ]
                for v in values:
                    if maxValue < int(v['alertCode']):
                        maxValue = int(v['alertCode'])
                #print(maxValue)
                self.alerts.emit( values )
                
                return maxValue#len(values)

            def getFieldsName():
                fields = list( dbAlerts.FIELDSDEF.keys() )
                toField = fields.index('detectedAt') + 1
                fields = fields[:toField]
                return " ".join( fields ) + " cars { id carCode } geometry { geom }"
            
            fieldsName =  getFieldsName()
            s_territoryIds = ','.join( [ str(v) for v in territoryIds ] )
            offset = 0
            previousLast = 0
            while True:
                values = {
                    'startDetectedAt': startDetectedAt, 'endDetectedAt': endDetectedAt,
                    'territoryIds': s_territoryIds,
                    'limit': self.LIMIT, 'offset': offset,
                    'fields': fieldsName
                }
                #print('Requesting OFFSET=')
                #print(offset)

                #print(values)
                #self.message.emit(values, Qgis.Warning)
                last = request( values )
                #print('Last ID:')
                #print(last)
                if task.isCanceled():
                    self.message.emit('Canceled by user', Qgis.Warning)
                    return
                if last == -1:
                    return
                if previousLast == last:
                    break
                offset = offset + self.LIMIT#total
                previousLast = last
                self.status.emit(f"Receiving {offset}...")

            return { 'total': offset + total }

        def finished(exception, dataResult=None):
            self.finishedAlert.emit()
            self.taskAlerts = None
            msg = f"Finished {dataResult['total']} alerts" if dataResult else ''
            self.status.emit( msg )

        task = QgsTask.fromFunction('Alert Task', run, on_finished=finished )
        task.setDependentLayers( [ dbAlerts.layer ] )
        self.taskAlerts = task
        self.taskManager.addTask( task )
        # Debug
        # r = run( task )
        # finished(None, r)

    def cancelAlerts(self):
        if self.taskAlerts:
            self.taskAlerts.cancel()

    def getImages(self, alertId):
        def run(task):
            def getThumbnail(url):
                err = self.request.get( QNetworkRequest( QUrl( url ) ) )
                if not err == QgsBlockingNetworkRequest.NoError:
                    self.message.emit( self.request.errorMessage(), Qgis.Critical )
                    return None
                data = self.request.reply().content().data()
                pixmap = QPixmap()
                pixmap.loadFromData( data )
                return pixmap

            values = { 'alertId': alertId }
            data = self._replaceQuery( values, self.Q_IMAGES )
            response = self._request( data )
            print('REQUEST [IMAGE data]:')
            print(data)
            if not response:
                self.message.emit( self.request.errorMessage(), Qgis.Critical )
                return None
            data = response['data']['alertReport']['images']
            print('IMAGE data:')
            print(data)
            for k in ( 'before', 'after'):
                data[ k ]['thumbnail'] = getThumbnail( data[k]['url'] )
            return data

        def finished(exception, dataResult=None):
            self.taskImage = None
            if dataResult:
                self.images.emit( dataResult )

        task = QgsTask.fromFunction('Alert/Get Images Task', run, on_finished=finished )
        self.taskImage = task
        self.taskManager.addTask( task )
        # Debug
        #r = run( task )
        #finished(None, r)


class TerritoryBbox():
    FIELDSDEF = {
        'id': 'string(25)'
    }
    CRS = QgsCoordinateReferenceSystem('EPSG:4674')
    CSV = 'territory_bbox.csv'
    def __init__(self):
        self.mapCanvas = QgsUtils.iface.mapCanvas()
        self.taskManager = QgsApplication.taskManager()
        self.threadMain = QgsApplication.instance().thread()
        self.csv = os.path.join( os.path.dirname( __file__ ),  self.CSV )
        self.project = QgsProject.instance()
        self.layer  = None

    def __del__(self):
        if self.layer:
            self.layer = None

    def _createLayer(self):
        name = self.CSV
        l_fields = [ f"field={k}:{v}" for k,v in self.FIELDSDEF.items() ]
        l_fields.insert( 0, f"polygon?crs={self.CRS.authid().lower()}" )
        l_fields.append( "index=yes" )
        uri = '&'.join( l_fields )
        return QgsVectorLayer( uri, name, 'memory' )

    def setLayer(self):
        def run(task):
            layer = self._createLayer()
            provider = layer.dataProvider()
            with open( self.csv ) as csv_file:
                csv_reader = csv.reader( csv_file, delimiter=';')
                for row in csv_reader:
                    id, wkt = row[0], row[1]
                    feat = QgsFeature()
                    feat.setAttributes( [ id ] )
                    geom = QgsGeometry.fromWkt( wkt )
                    feat.setGeometry( geom )
                    provider.addFeature( feat )
            layer.moveToThread( self.threadMain )
            return { 'layer': layer }

        def finished(exception, dataResult=None):
            if dataResult:
                self.layer = dataResult['layer']

        task = QgsTask.fromFunction('Alert Task', run, on_finished=finished )
        self.taskManager.addTask( task )
        # Debug
        # Comment layer.moveToThread(self.threadMain )
        # r = run( task, layer )
        # finished(None, r)

    def getIdsCanvas(self):
        crs = self.project.crs()
        extent = self.mapCanvas.extent()
        if not crs  == self.CRS:
            ct = QgsCoordinateTransform( crs, self.CRS, self.project )
            extent = ct.transform( extent )
        fr = QgsFeatureRequest().setFilterRect( extent ) 
        features = self.layer.getFeatures( fr )
        return [ feat['id'] for feat in features ]


class DbAlerts(QObject):
    FIELDSDEF = {
        'alertCode': 'string(25)',
        'source': 'string(-1)',
        'areaHa': 'double',
        'detectedAt': 'date', # Need be the last field for API_MapBiomasAlert.getAlerts.run.getFieldsName
        'carCode': 'string(-1)',
        'carId': 'string(-1)',
    }
    CRS = QgsCoordinateReferenceSystem('EPSG:4674')
    def __init__(self, layer):
        super().__init__()
        self.layer = layer
        self.project = QgsProject.instance()
        self.project.layerWillBeRemoved.connect( self.removeLayer )

    @staticmethod
    def transformItemWFS(item,context):
        # Source
        new_item = {}
        #new_item.setFields(DbAlerts.fi)
        #new_item.setGeometry(QgsGeometry.fromMultiPolygonXY(item.geometry))
        #new_item.setGeometry(item.geometry)
        new_item['alertCode'] = item['alert_code']
        new_item['source'] = item['source'] 
        new_item['areaHa'] = item['area_ha']
        # Date
        detectedAt = item['detected_at'].split('/')
        detectedAt.reverse()
        new_item['detectedAt'] = '-'.join( detectedAt )
        cars = json.loads(item['cars'])
        new_item['carCode'] = [ v['car_code'] for v in cars ]
        new_item['carId'] = [ str(v['id']) for v in cars]
        new_item['carId'] = ','.join( new_item['carId'] )
        new_item['carCode'] = ','.join( new_item['carCode'] )
        # carCode
        #item['carCode'] = [ v['carCode'] for v in item['cars'] ]
        #item['carId'] = [ str(v['id']) for v in item['cars']]
        #item['carId'] = ','.join( item['carId'] )
        #item['carCode'] = ','.join( item['carCode'] )
        #del item['cars']
        # Geometry
        #geom, srid = Geometry_WKB.getQgsGeometry_SRID( item['geometry']['geom'] )
        #del item['geometry']
        #del item['alert_code']
        new_item['geom'] =  item.geometry()
        new_item['srid'] = '4674'
        #context.setProgress(98)
        #context.status.emit(f"Receiving...")
        return new_item

    @staticmethod
    def transformItem(item):
        # Source
        item['source'] = ','.join( item['source'] )
        # Date
        detectedAt = item['detectedAt'].split('/')
        detectedAt.reverse()
        item['detectedAt'] = '-'.join( detectedAt )
        # carCode
        item['carCode'] = [ v['carCode'] for v in item['cars'] ]
        item['carId'] = [ str(v['id']) for v in item['cars']]
        item['carId'] = ','.join( item['carId'] )
        item['carCode'] = ','.join( item['carCode'] )
        del item['cars']
        # Geometry
        geom, srid = Geometry_WKB.getQgsGeometry_SRID( item['geometry']['geom'] )
        del item['geometry']
        item['geom'] = geom
        item['srid'] = srid
        
        return item

    @staticmethod
    def createLayer():
        name = 'Alert ..'
        l_fields = [ f"field={k}:{v}" for k,v in DbAlerts.FIELDSDEF.items() ]
        l_fields.insert( 0, f"Multipolygon?crs={DbAlerts.CRS.authid().lower()}" )
        l_fields.append( "index=yes" )
        uri = '&'.join( l_fields )
        return QgsVectorLayer( uri, name, 'memory' )

    def setLayer(self, startDetectedAt, endDetectedAt):
        name = f"Alert {startDetectedAt} .. {endDetectedAt}"
        self.layer.dataProvider().truncate()
        self.layer.setName( name )
        self.layer.updateExtents()
        self.layer.triggerRepaint()

    @pyqtSlot(list)
    def addFeatures(self, data):
        def add(item):
            # Geometry
            crs = QgsCoordinateReferenceSystem(f"EPSG:{item['srid']}")
            if not crs == self.CRS:
                ct = QgsCoordinateTransform( crs, self.CRS, self.project )
                item['geom'].transform( ct )
            # Add
            atts = [ item[k] for k in self.FIELDSDEF ]
            feat = QgsFeature()
            feat.setAttributes( atts )
            feat.setGeometry( item['geom'])
            provider.addFeature( feat )

        provider = self.layer.dataProvider()
        for item in data:
            add( item )
        self.layer.updateExtents()
        self.layer.triggerRepaint()

    @pyqtSlot(str)
    def removeLayer(self, layerId):
        if self.layer and layerId == self.layer.id():
            self.layer.dataProvider().truncate()
            self.layer = None
