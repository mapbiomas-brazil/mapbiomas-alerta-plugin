<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.16.5-Hannover" styleCategories="Symbology|Fields|CustomProperties|Temporal">
  <temporal accumulate="1" startField="detectedAt" endField="" durationField="" durationUnit="d" fixedDuration="1" mode="1" endExpression="" enabled="1" startExpression="">
    <fixedRange>
      <start></start>
      <end></end>
    </fixedRange>
  </temporal>
  <renderer-v2 enableorderby="0" forceraster="0" type="singleSymbol" symbollevels="0">
    <symbols>
      <symbol name="0" clip_to_extent="1" alpha="0.465" type="fill" force_rhr="0">
        <layer class="SimpleFill" enabled="1" locked="0" pass="0">
          <prop k="border_width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="color" v="51,189,223,255"/>
          <prop k="joinstyle" v="bevel"/>
          <prop k="offset" v="0,0"/>
          <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_unit" v="MM"/>
          <prop k="outline_color" v="35,35,35,255"/>
          <prop k="outline_style" v="solid"/>
          <prop k="outline_width" v="0.26"/>
          <prop k="outline_width_unit" v="MM"/>
          <prop k="style" v="solid"/>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" type="QString" value=""/>
              <Option name="properties"/>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
    </symbols>
    <rotation/>
    <sizescale/>
  </renderer-v2>
  <customproperties>
    <property key="MapBiomasAlert" value="1"/>
    <property key="embeddedWidgets/0/id" value="LayerMapBiomasAlertWidgetProvider"/>
    <property key="embeddedWidgets/count" value="1"/>
    <property key="variableNames"/>
    <property key="variableValues"/>
  </customproperties>
  <blendMode>0</blendMode>
  <featureBlendMode>0</featureBlendMode>
  <fieldConfiguration>
    <field name="alertCode" configurationFlags="None"/>
    <field name="source" configurationFlags="None"/>
    <field name="areaHa" configurationFlags="None"/>
    <field name="detectedAt" configurationFlags="None"/>
    <field name="carCode" configurationFlags="None"/>
  </fieldConfiguration>
  <aliases>
    <alias name="" field="alertCode" index="0"/>
    <alias name="" field="source" index="1"/>
    <alias name="" field="areaHa" index="2"/>
    <alias name="" field="detectedAt" index="3"/>
    <alias name="" field="carCode" index="4"/>
  </aliases>
  <defaults>
    <default expression="" applyOnUpdate="0" field="alertCode"/>
    <default expression="" applyOnUpdate="0" field="source"/>
    <default expression="" applyOnUpdate="0" field="areaHa"/>
    <default expression="" applyOnUpdate="0" field="detectedAt"/>
    <default expression="" applyOnUpdate="0" field="carCode"/>
  </defaults>
  <constraints>
    <constraint unique_strength="0" field="alertCode" notnull_strength="0" exp_strength="0" constraints="0"/>
    <constraint unique_strength="0" field="source" notnull_strength="0" exp_strength="0" constraints="0"/>
    <constraint unique_strength="0" field="areaHa" notnull_strength="0" exp_strength="0" constraints="0"/>
    <constraint unique_strength="0" field="detectedAt" notnull_strength="0" exp_strength="0" constraints="0"/>
    <constraint unique_strength="0" field="carCode" notnull_strength="0" exp_strength="0" constraints="0"/>
  </constraints>
  <constraintExpressions>
    <constraint exp="" field="alertCode" desc=""/>
    <constraint exp="" field="source" desc=""/>
    <constraint exp="" field="areaHa" desc=""/>
    <constraint exp="" field="detectedAt" desc=""/>
    <constraint exp="" field="carCode" desc=""/>
  </constraintExpressions>
  <expressionfields/>
  <layerGeometryType>2</layerGeometryType>
</qgis>
