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


    map.on('singleclick', function(evt) {
        if(document.getElementsByName("longitud")[0].tagName=="INPUT"){
            var feature = map.forEachFeatureAtPixel(evt.pixel, function(feature, layer) {
                return feature;
            });
    
            var coordinate = ol.proj.toLonLat(evt.coordinate);
            var prettyCoord = ol.proj.transform(evt.coordinate, 'EPSG:900913', 'EPSG:4326')
    
            var urlCal = 'https://nominatim.openstreetmap.org/search.php?q=' + prettyCoord[1] + '%2C%20' + prettyCoord[0] + '&addressdetails=1&format=jsonv2';
            var xmlHttp = new XMLHttpRequest();
            xmlHttp.open("GET", urlCal, false);
            xmlHttp.send(null);
    
            var createCharge = JSON.parse(xmlHttp.responseText);
    
            map.getLayers().forEach(layer => {
                try {
                    if (layer.get('name') && layer.get('name') == 'MapLayer') {
                        map.removeLayer(layer)
                    }
                } catch (ex) {}
            });
    
                
                    
    
                    $('[name*="calle"]').val(createCharge[0]['address']['road'])
                    $('[name*="colonia"]').val(createCharge[0]['address']['neighbourhood'])
    
                    direccion = createCharge[0]['display_name'];
    
                    $('[name*="latitud"]').val(prettyCoord[1])
                    $('[name*="longitud"]').val(prettyCoord[0])
    
                    localStorage.setItem('latitud', prettyCoord[1]);
                    localStorage.setItem('longitud', prettyCoord[0]);
    
                    var MarkerIcon = new ol.Feature({
                        geometry: new ol.geom.Point(ol.proj.fromLonLat([prettyCoord[0], prettyCoord[1]])),
                        name: 'MapLayer',
                        desc: '<label>Details</label>'
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
    
                    MapLayer.setZIndex(0);
                    MapLayer.set('name', 'MapLayer');
                    //MapLayer.setZIndex(999);
                    map.addLayer(MapLayer);
    
                    
                    var saveUrl = "catax/getdata/";
                    var f = new FormData();
    
                    f.append("latitud", prettyCoord[1]);
                    f.append("longitud", prettyCoord[0]);
                    f.append("direccion", createCharge[0]['display_name']);
                    f.append("colonia", localStorage.getItem('colonia'));
                    f.append("calle", createCharge[0]['address']['road'] );
                    
                    var settings = {
                        "async": true,
                        "crossDomain": true,
                        "url": serv+saveUrl,
                        "method": "POST",
                        "processData": false,
                        "contentType": false,
                        "mimeType": "multipart/form-data",
                        "data": f
                    }
    
                    $.ajax(settings).done(function(response) {
                        console.log('llamado');
                        responseSend = JSON.parse(response);
                    });
    

                    if(onchangenedded && dotrdy){
                        dotrdy = false;
                        $(".ref").val($(".ref").val()+" ").trigger('change'); //horrible hack para mandar un value a guardar y que tome todos los datos del mapa
                    }
                }
            
        
    });
    

    
    
}







