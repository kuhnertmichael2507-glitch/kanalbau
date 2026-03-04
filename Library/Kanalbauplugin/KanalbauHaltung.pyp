<?xml version="1.0" encoding="utf-8"?>
<Element>
  <Script>
    <Name>Kanalbauplugin\KanalbauHaltung.py</Name>
    <Title>Kanalbauhaltung</Title>
    <Version>1.0</Version>
    <ReadLastInput>True</ReadLastInput>
  </Script>

  <!-- ================================================================
       SEITE 1: ÜBERSICHT
       Haltungsname, Schachtnamen, Haltungslänge, Gefälle, Stationierung
       ================================================================ -->
  <Page>
    <Name>Uebersicht</Name>
    <Text>Übersicht</Text>

    <Parameter>
      <Name>ExpAllgemein</Name>
      <Text>Allgemeine Angaben</Text>
      <ValueType>Expander</ValueType>

      <Parameter>
        <Name>HaltungsName</Name>
        <Text>Haltungsbezeichnung</Text>
        <Value>H001</Value>
        <ValueType>String</ValueType>
      </Parameter>

      <Parameter>
        <Name>StartschachtName</Name>
        <Text>Startschacht</Text>
        <Value>S001</Value>
        <ValueType>String</ValueType>
      </Parameter>

      <Parameter>
        <Name>EndschachtName</Name>
        <Text>Endschacht</Text>
        <Value>S002</Value>
        <ValueType>String</ValueType>
      </Parameter>
    </Parameter>

    <Parameter>
      <Name>ExpTrassenGeometrie</Name>
      <Text>Trassengeometrie</Text>
      <ValueType>Expander</ValueType>

      <Parameter>
        <Name>Haltungslaenge</Name>
        <Text>Haltungslänge (mm)</Text>
        <Value>20000</Value>
        <ValueType>Length</ValueType>
        <MinValue>1000</MinValue>
        <MaxValue>200000</MaxValue>
      </Parameter>

      <Parameter>
        <Name>Gefalle</Name>
        <Text>Gefälle (%)</Text>
        <Value>1.5</Value>
        <ValueType>Double</ValueType>
        <MinValue>0.0</MinValue>
        <MaxValue>20.0</MaxValue>
      </Parameter>
    </Parameter>

    <Parameter>
      <Name>ExpStationierung</Name>
      <Text>Stationierung</Text>
      <ValueType>Expander</ValueType>

      <Parameter>
        <Name>StationierungsAbstand</Name>
        <Text>Stationierungsabstand (mm)</Text>
        <Value>5000</Value>
        <ValueType>Length</ValueType>
        <MinValue>500</MinValue>
        <MaxValue>50000</MaxValue>
      </Parameter>

      <Parameter>
        <Name>StationierungsOffset</Name>
        <Text>Startstation (m)</Text>
        <Value>0.0</Value>
        <ValueType>Double</ValueType>
        <MinValue>0.0</MinValue>
      </Parameter>
    </Parameter>

  </Page>

  <!-- ================================================================
       SEITE 2: STARTSCHACHT
       ================================================================ -->
  <Page>
    <Name>Startschacht</Name>
    <Text>Startschacht</Text>

    <Parameter>
      <Name>ExpStartAbmessung</Name>
      <Text>Schachtabmessungen</Text>
      <ValueType>Expander</ValueType>

      <Parameter>
        <Name>StartSchachtDN</Name>
        <Text>Schacht-DN (mm)</Text>
        <Value>1000</Value>
        <ValueList>800|1000|1200|1500|2000</ValueList>
        <ValueType>IntegerComboBox</ValueType>
      </Parameter>

      <Parameter>
        <Name>StartWandstaerke</Name>
        <Text>Wandstärke (mm)</Text>
        <Value>120</Value>
        <ValueType>Length</ValueType>
        <MinValue>50</MinValue>
        <MaxValue>400</MaxValue>
      </Parameter>

      <Parameter>
        <Name>StartSchachtTiefe</Name>
        <Text>Schachttiefe (mm)</Text>
        <Value>3000</Value>
        <ValueType>Length</ValueType>
        <MinValue>500</MinValue>
        <MaxValue>20000</MaxValue>
      </Parameter>
    </Parameter>

    <Parameter>
      <Name>ExpStartKonus</Name>
      <Text>Konus (Verjüngung)</Text>
      <ValueType>Expander</ValueType>

      <Parameter>
        <Name>StartMitKonus</Name>
        <Text>Konus vorhanden</Text>
        <Value>True</Value>
        <ValueType>CheckBox</ValueType>
      </Parameter>

      <Parameter>
        <Name>StartKonusHoehe</Name>
        <Text>Konushöhe (mm)</Text>
        <Value>600</Value>
        <ValueType>Length</ValueType>
        <MinValue>200</MinValue>
        <MaxValue>2000</MaxValue>
        <Visible>StartMitKonus == True</Visible>
      </Parameter>

      <Parameter>
        <Name>StartKonusDN_oben</Name>
        <Text>Konus-DN oben (mm)</Text>
        <Value>625</Value>
        <ValueType>Length</ValueType>
        <MinValue>400</MinValue>
        <MaxValue>1500</MaxValue>
        <Visible>StartMitKonus == True</Visible>
      </Parameter>
    </Parameter>

    <Parameter>
      <Name>ExpStartAufbau</Name>
      <Text>Aufbau &amp; Abdeckung</Text>
      <ValueType>Expander</ValueType>

      <Parameter>
        <Name>StartAufbauHoehe</Name>
        <Text>Aufbauhöhe (mm)</Text>
        <Value>300</Value>
        <ValueType>Length</ValueType>
        <MinValue>0</MinValue>
        <MaxValue>1000</MaxValue>
      </Parameter>

      <Parameter>
        <Name>StartAufbauDN</Name>
        <Text>Aufbau-DN (mm)</Text>
        <Value>625</Value>
        <ValueType>Length</ValueType>
        <MinValue>400</MinValue>
        <MaxValue>1000</MaxValue>
      </Parameter>
    </Parameter>

    <Parameter>
      <Name>ExpStartSohlplatte</Name>
      <Text>Sohlplatte</Text>
      <ValueType>Expander</ValueType>

      <Parameter>
        <Name>StartSohlplatteH</Name>
        <Text>Sohlplattenstärke (mm)</Text>
        <Value>200</Value>
        <ValueType>Length</ValueType>
        <MinValue>100</MinValue>
        <MaxValue>500</MaxValue>
      </Parameter>
    </Parameter>

  </Page>

  <!-- ================================================================
       SEITE 3: ROHRLEITUNG
       ================================================================ -->
  <Page>
    <Name>Rohrleitung</Name>
    <Text>Rohrleitung</Text>

    <Parameter>
      <Name>ExpRohrAbmessung</Name>
      <Text>Rohrabmessungen (aus CSV)</Text>
      <ValueType>Expander</ValueType>

      <Parameter>
        <Name>RohrDN</Name>
        <Text>Nennweite DN (mm)</Text>
        <Value>300</Value>
        <ValueList>100|150|200|250|300|400|500|600|700|800|1000|1200</ValueList>
        <ValueType>IntegerComboBox</ValueType>
      </Parameter>

      <Parameter>
        <Name>RohrWandstaerke</Name>
        <Text>Wandstärke (mm)</Text>
        <Value>35</Value>
        <ValueType>Length</ValueType>
        <MinValue>5</MinValue>
        <MaxValue>300</MaxValue>
      </Parameter>

      <Parameter>
        <Name>RohrMaterial</Name>
        <Text>Material</Text>
        <Value>Beton</Value>
        <ValueList>Beton|PVC|Steinzeug|GFK|Stahl|Gusseisen</ValueList>
        <ValueType>StringComboBox</ValueType>
      </Parameter>
    </Parameter>

    <Parameter>
      <Name>ExpRohrStationierung</Name>
      <Text>Stationierungsanzeige</Text>
      <ValueType>Expander</ValueType>

      <Parameter>
        <Name>RohrMitStationierung</Name>
        <Text>Stationierung anzeigen</Text>
        <Value>True</Value>
        <ValueType>CheckBox</ValueType>
      </Parameter>

      <Parameter>
        <Name>StationierungsTextHoehe</Name>
        <Text>Texthöhe (mm)</Text>
        <Value>200</Value>
        <ValueType>Length</ValueType>
        <MinValue>50</MinValue>
        <MaxValue>1000</MaxValue>
        <Visible>RohrMitStationierung == True</Visible>
      </Parameter>

      <Parameter>
        <Name>StationierungsTextOffset</Name>
        <Text>Textabstand zur Achse (mm)</Text>
        <Value>300</Value>
        <ValueType>Length</ValueType>
        <MinValue>0</MinValue>
        <MaxValue>2000</MaxValue>
        <Visible>RohrMitStationierung == True</Visible>
      </Parameter>
    </Parameter>

  </Page>

  <!-- ================================================================
       SEITE 4: ENDSCHACHT
       ================================================================ -->
  <Page>
    <Name>Endschacht</Name>
    <Text>Endschacht</Text>

    <Parameter>
      <Name>ExpEndAbmessung</Name>
      <Text>Schachtabmessungen</Text>
      <ValueType>Expander</ValueType>

      <Parameter>
        <Name>EndSchachtDN</Name>
        <Text>Schacht-DN (mm)</Text>
        <Value>1000</Value>
        <ValueList>800|1000|1200|1500|2000</ValueList>
        <ValueType>IntegerComboBox</ValueType>
      </Parameter>

      <Parameter>
        <Name>EndWandstaerke</Name>
        <Text>Wandstärke (mm)</Text>
        <Value>120</Value>
        <ValueType>Length</ValueType>
        <MinValue>50</MinValue>
        <MaxValue>400</MaxValue>
      </Parameter>

      <Parameter>
        <Name>EndSchachtTiefe</Name>
        <Text>Schachttiefe (mm)</Text>
        <Value>3150</Value>
        <ValueType>Length</ValueType>
        <MinValue>500</MinValue>
        <MaxValue>20000</MaxValue>
      </Parameter>
    </Parameter>

    <Parameter>
      <Name>ExpEndKonus</Name>
      <Text>Konus (Verjüngung)</Text>
      <ValueType>Expander</ValueType>

      <Parameter>
        <Name>EndMitKonus</Name>
        <Text>Konus vorhanden</Text>
        <Value>True</Value>
        <ValueType>CheckBox</ValueType>
      </Parameter>

      <Parameter>
        <Name>EndKonusHoehe</Name>
        <Text>Konushöhe (mm)</Text>
        <Value>600</Value>
        <ValueType>Length</ValueType>
        <MinValue>200</MinValue>
        <MaxValue>2000</MaxValue>
        <Visible>EndMitKonus == True</Visible>
      </Parameter>

      <Parameter>
        <Name>EndKonusDN_oben</Name>
        <Text>Konus-DN oben (mm)</Text>
        <Value>625</Value>
        <ValueType>Length</ValueType>
        <MinValue>400</MinValue>
        <MaxValue>1500</MaxValue>
        <Visible>EndMitKonus == True</Visible>
      </Parameter>
    </Parameter>

    <Parameter>
      <Name>ExpEndAufbau</Name>
      <Text>Aufbau &amp; Abdeckung</Text>
      <ValueType>Expander</ValueType>

      <Parameter>
        <Name>EndAufbauHoehe</Name>
        <Text>Aufbauhöhe (mm)</Text>
        <Value>300</Value>
        <ValueType>Length</ValueType>
        <MinValue>0</MinValue>
        <MaxValue>1000</MaxValue>
      </Parameter>

      <Parameter>
        <Name>EndAufbauDN</Name>
        <Text>Aufbau-DN (mm)</Text>
        <Value>625</Value>
        <ValueType>Length</ValueType>
        <MinValue>400</MinValue>
        <MaxValue>1000</MaxValue>
      </Parameter>
    </Parameter>

    <Parameter>
      <Name>ExpEndSohlplatte</Name>
      <Text>Sohlplatte</Text>
      <ValueType>Expander</ValueType>

      <Parameter>
        <Name>EndSohlplatteH</Name>
        <Text>Sohlplattenstärke (mm)</Text>
        <Value>200</Value>
        <ValueType>Length</ValueType>
        <MinValue>100</MinValue>
        <MaxValue>500</MaxValue>
      </Parameter>
    </Parameter>

  </Page>

</Element>
