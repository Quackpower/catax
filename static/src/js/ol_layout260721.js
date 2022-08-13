//var serv = "https://reportescatax.xalapa.gob.mx/";
var serv = "http://140.82.0.198/";
//var serv = "http://localhost:8069/"
var map;
var onchangenedded=false;
var dotrdy=true;

(function() {
        traerMapa(false)
})();

    

function traerMapa(con_capa){
    
    

    var latM,lonM,puntoDetectado=false;
    if(document.getElementsByName("longitud")[0].innerHTML!=""){
        lonM = document.getElementsByName("longitud")[0].innerHTML;
        puntoDetectado = true
    }
    else{
        lonM = document.getElementsByName("longitud")[0].value
        onchangenedded=true;
        if(lonM!=undefined && lonM!=""){
            puntoDetectado = true
        }
        else{
            puntoDetectado = false
        }
        
    }

    if(document.getElementsByName("latitud")[0].innerHTML!=""){
        latM = document.getElementsByName("latitud")[0].innerHTML;
        puntoDetectado = true
    }
    else{
        latM = document.getElementsByName("latitud")[0].value
        if(latM!=undefined && latM!=""){
            puntoDetectado = true
        }
        else{
            puntoDetectado = false
        }
    }

    console.log(puntoDetectado);

    if(puntoDetectado){
        var view = new ol.View({
            center: ol.proj.transform([parseFloat(lonM), parseFloat(latM)], 'EPSG:4326', 'EPSG:900913'),
            zoom: 14,
            minZoom: 12,
        });

        map = new ol.Map({
            target: 'map',
            layers: [
                new ol.layer.Tile({
                    title: 'OSM',
                    type: 'base',
                    visible: true,
                    source: new ol.source.OSM()
                })
            ],
            view: view
        })

        var MarkerIcon = new ol.Feature({
            geometry: new ol.geom.Point(ol.proj.fromLonLat([parseFloat(lonM),parseFloat(latM)])),
            name: 'MapLayer',
        })
    
        MarkerIcon.setStyle(new ol.style.Style({
            image: new ol.style.Icon({
                anchor: [0.5, 50],
                anchorXUnits: 'fraction',
                anchorYUnits: 'pixels',
                src: '/catax/static/images/marcador-de-p.png'
            })
        }));
    
        var MapSource = new ol.source.Vector({
            features: [
                MarkerIcon
            ]
        })
    
        var MapLayer = new ol.layer.Vector({
            source: MapSource
        });
    
        MapLayer.set('name', 'MapLayer');
        MapLayer.setZIndex(999);
        map.addLayer(MapLayer);
    }
    else{
        var view = new ol.View({
            center: ol.proj.transform([-96.9601074,19.4544924], 'EPSG:4326', 'EPSG:900913'),
            zoom: 14,
            minZoom: 12,
        });

        map = new ol.Map({
            target: 'map',
            layers: [
                new ol.layer.Tile({
                    title: 'OSM',
                    type: 'base',
                    visible: true,
                    source: new ol.source.OSM()
                })
            ],
            view: view
        })

        var MarkerIcon = new ol.Feature({
            geometry: new ol.geom.Point(ol.proj.transform([-96.9601074,19.4544924], 'EPSG:4326', 'EPSG:900913')),
            name: 'MapLayer',
        })
        MarkerIcon.setStyle(new ol.style.Style({
            image: new ol.style.Icon({
                anchor: [0.5, 50],
                anchorXUnits: 'fraction',
                anchorYUnits: 'pixels',
                src: '/catax/static/images/marcador-de-p.png'
            })
        }));
    
        var MapSource = new ol.source.Vector({
            features: [
                MarkerIcon
            ]
        })
    
        var MapLayer = new ol.layer.Vector({
            source: MapSource
        });
    
        MapLayer.set('name', 'MapLayer');
        MapLayer.setZIndex(999);
        map.addLayer(MapLayer);
    }
    

    
    
}







