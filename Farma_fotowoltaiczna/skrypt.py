import arcpy
from arcpy import env
from arcpy.sa import *
import os
# Ustawienie ścieżki do geobazy
arcpy.env.workspace = r"C:\Users\user\Documents\ArcGIS\Projects\MyProject7\MyProject7.gdb"

# Definicja warstw projektu
swrs="swrs" # Warstwa cieków wodnych
ptwp="ptwp" # Warstwa wód powierzchniowych 
nmt="NMT_tif" # Numeryczny Model Terenu
gmina="gmina_swieradow" # Granica gminy
budynki = "bubd" # Warstwa budynków
ptlz="ptlz" # Warstwa lasów
skjz="skjz" # Warstwa dróg
raster_wezly= "link_raster_tif" # Raster wezłów komunikacyjnych
dzialki="dzialki_lubanski" # Warstwa działek
linie_energetyczne="suln" # Warstwa linii energetycznych
# Warstwy tematyczne
ptzb="ptzb" 
ptut="ptut" 
pttr="pttr"
ptrk="ptrk"
ptpl="ptpl"
ptnz="ptnz"
ptkm="ptkm"
ptgn="ptgn"
gmina_bufor="gmina_swieradow_bufor" #Bufor wokół gminy

# Przycięcie NMT do obszaru gminy
o_NMT_przyciety = ExtractByMask(nmt, gmina_bufor, "INSIDE")
o_NMT_przyciety.save(arcpy.env.workspace + r"\o_przycietyNMT")

cell_size=arcpy.env.workspace+r"\o_przycietyNMT"

# Tworzenie bufora wokół cieków wodnych
arcpy.analysis.Buffer(
    in_features=swrs,
    out_feature_class=arcpy.env.workspace + r"\o_swrs_buffer",
    buffer_distance_or_field="1 Meters",
    line_side="FULL",
    line_end_type="ROUND",
    dissolve_option="NONE",
    dissolve_field=None,
    method="PLANAR"
)

# Połączenie buforu rzek z wodami powierzchniowymi
arcpy.management.Merge(["o_swrs_buffer", ptwp], 
                       arcpy.env.workspace + "\o_wody_powierzchniowe", "", "NO_SOURCE_INFO")

#  Obliczenie Euclidean Distance od wód powierzchniowych
o_euc_wody = arcpy.sa.EucDistance(
    in_source_data="o_wody_powierzchniowe",
    maximum_distance=None,
    cell_size=arcpy.env.workspace + r"\o_przycietyNMT",
    out_direction_raster=None,
    distance_method="PLANAR",
    in_barrier_data=None,
    out_back_direction_raster=None
)
o_euc_wody.save(arcpy.env.workspace + r"\o_EucDist_wody_powierzchniowe")

# Tworzenie funckji rozmyteh dla odległości od wód powierzchniowych
# Funkcja ma gwałtowny spadek od 100 do 100,1 m, a od 160 m maleje liniowo do 912 m
o_fuzzy_wody1 = arcpy.sa.FuzzyMembership(
    in_raster="o_EucDist_wody_powierzchniowe",
    fuzzy_function="LINEAR 100 100,1",
    hedge="NONE"
)
o_fuzzy_wody1.save(arcpy.env.workspace + r"\o_FuzzyMe_wody1")

o_fuzzy_wody2 = arcpy.sa.FuzzyMembership(
    in_raster="o_EucDist_wody_powierzchniowe",
    fuzzy_function="LINEAR 912 160",
    hedge="NONE"
)
o_fuzzy_wody2.save(arcpy.env.workspace + r"\o_FuzzyMe_wody2")

# Połączenie dwóch funkcji rozmytych
o_odl_od_wod = arcpy.sa.FuzzyOverlay(
    in_rasters="o_FuzzyMe_wody1;o_FuzzyMe_wody2",
    overlay_type="AND",
    gamma=0.9
)
o_odl_od_wod.save(arcpy.env.workspace + r"\o_Fuzzy_wody_pow1")


# Wybór budynków mieszkalnych
where_clause = "FOBUD = 'budynki mieszkalne'"
selected_buildings_layer = "SelectedBuildingsLayer"
arcpy.MakeFeatureLayer_management(budynki, selected_buildings_layer, where_clause)

# Obliczenie Euclidean Distance od budynków mieszkalnych
o_Euc_Dist_bubd = arcpy.sa.EucDistance(
    in_source_data=selected_buildings_layer,
    maximum_distance=None,
    cell_size=arcpy.env.workspace + r"\o_przycietyNMT",
    out_direction_raster=None,
    distance_method="PLANAR",
    in_barrier_data=None,
    out_back_direction_raster=None
)
o_Euc_Dist_bubd.save(arcpy.env.workspace + r"\o_EucDist_bubd11")
# Usunięcie warstwy tymczasowej
arcpy.Delete_management(selected_buildings_layer)

# Tworzenie funkcji rozmytej
# Funkcja maleje od 150,1 m do 1800 m
o_odl_od_bud = arcpy.sa.FuzzyMembership(
    in_raster="o_EucDist_bubd11",
    fuzzy_function="LINEAR 150,1 1800",
    hedge="NONE"
)
o_odl_od_bud.save(arcpy.env.workspace + r"\o_FuzzyMe_Euc_bubd")



# Euclidean Distance od lasów
o_Euc_Dist_lasy = arcpy.sa.EucDistance(
    in_source_data=ptlz,
    maximum_distance=None,
    cell_size=arcpy.env.workspace + r"\o_przycietyNMT",
    out_direction_raster=None,
    distance_method="PLANAR",
    in_barrier_data=None,
    out_back_direction_raster=None
)
o_Euc_Dist_lasy.save(arcpy.env.workspace + r"\o_Eucdist_ptlz")

# Funkcja maleje od 15 do 100 m
odl_od_lasow = arcpy.sa.FuzzyMembership(
    in_raster="o_Eucdist_ptlz",
    fuzzy_function="LINEAR 15 100",
    hedge="NONE"
)
odl_od_lasow.save(arcpy.env.workspace + r"\o_FuzzyMe_Eucptlz")

# Obliczanie nachylenia terenu
o_slope = arcpy.sa.Slope(
    in_raster=nmt,
    output_measurement="PERCENT_RISE",
    z_factor=1,
    method="PLANAR",
    z_unit="METER",
    analysis_target_device="GPU_THEN_CPU"
)
o_slope.save(arcpy.env.workspace + r"\o_Slope_NMT11")

# Tworzenie funkcji rozmytej, od 5 do 10 % nachylenia funckja maleja, powyżej 10 wartości są równe 0
o_nachylenie = arcpy.sa.FuzzyMembership(
    in_raster="o_Slope_NMT11",
    fuzzy_function="LINEAR 10 5",
    hedge="NONE"
)
o_nachylenie.save(arcpy.env.workspace + r"\o_FuzzyMe_Eucpslope")

# Wybór stoków południowych i wschodnich
o_aspect = arcpy.sa.Aspect(
    in_raster=nmt,
    method="PLANAR",
    z_unit="METER",
    project_geodesic_azimuths="GEODESIC_AZIMUTHS",
    analysis_target_device="GPU_THEN_CPU"
)
o_aspect.save(arcpy.env.workspace + r"\o_Aspect_NMT11")

o_aspect_fuzzy1 = arcpy.sa.FuzzyMembership(
    in_raster="o_Aspect_NMT11",
    fuzzy_function="LINEAR 270 247,5",
    hedge="NONE"
)
o_aspect_fuzzy1.save(arcpy.env.workspace + r"\o_FuzzyMe_Aspe1")
o_aspect_fuzzy2 = arcpy.sa.FuzzyMembership(
    in_raster="o_Aspect_NMT11",
    fuzzy_function="LINEAR 90 112,5",
    hedge="NONE"
)
o_aspect_fuzzy2.save(arcpy.env.workspace + r"\o_FuzzyMe_Aspe2")
o_stoki_pol = arcpy.sa.FuzzyOverlay(
    in_rasters="o_FuzzyMe_Aspe1;o_FuzzyMe_Aspe2",
    overlay_type="AND",
    gamma=0.9
)
o_stoki_pol.save(arcpy.env.workspace + r"\o_FuzzyOv_Fuzz2")

# Wybór dróg o nawierzchni bitumicznej
where_clause = "MATE_NAWIE = 'masa bitumiczna'"
selected_roads_layer = "SelectedRoadsLayer"
arcpy.MakeFeatureLayer_management(skjz, selected_roads_layer, where_clause)
o_euc_roads = arcpy.sa.EucDistance(
    in_source_data=selected_roads_layer,
    maximum_distance=None,
    cell_size=cell_size,
    out_direction_raster=None,
    distance_method="PLANAR",
    in_barrier_data=None,
    out_back_direction_raster=None
)
o_euc_roads.save(arcpy.env.workspace + r"\o_EucDist_roads")
arcpy.Delete_management(selected_roads_layer)

# Tworzenie funkcji rozmytej
o_trasy_utwardzone = arcpy.sa.FuzzyMembership(
    in_raster="o_EucDist_roads",
    fuzzy_function="LINEAR 1313 1",
    hedge="NONE"
)
o_trasy_utwardzone.save(arcpy.env.workspace + r"\o_FuzzyMe_Euc_roads")

# Przycięcie buforu do granicy gminy
o_raster_wezly = arcpy.sa.ExtractByMask(
    in_raster=raster_wezly,
    in_mask_data=gmina_bufor,
    extraction_area="INSIDE")
o_raster_wezly.save(arcpy.env.workspace + r"\o_wyciety_link")

# Przypisanie 0 dla brakujących wartości
o_con = arcpy.ia.Con(
    in_conditional_raster="o_wyciety_link",
    in_true_raster_or_constant=0,
    in_false_raster_or_constant="o_wyciety_link",
    where_clause="VALUE IS NULL"
)
o_con.save(arcpy.env.workspace + r"\o_Con_wyciety_1")

# Tworzenie funkcji rozmytej
o_wezly_komunikacyjne = arcpy.sa.FuzzyMembership(
    in_raster="o_Con_wyciety_1",
    fuzzy_function="LINEAR 0 33990,6328125",
    hedge="NONE"
)
o_wezly_komunikacyjne.save(arcpy.env.workspace + r"\o_FuzzyMe_Con_1")


# Przekształcenie krytrium rzek na ostre
o_rzeki_ostre = arcpy.ia.Con(
    in_conditional_raster="o_Fuzzy_wody_pow1",
    in_true_raster_or_constant=0,
    in_false_raster_or_constant=1,
    where_clause="VALUE = 0"
)
o_rzeki_ostre.save(arcpy.env.workspace + r"\o_K1_rzeki_ostre")

# Przekształcenie kryterium budynków na ostre
o_bud_ostre = arcpy.ia.Con(
    in_conditional_raster="o_FuzzyMe_Euc_bubd",
    in_true_raster_or_constant=0,
    in_false_raster_or_constant=1,
    where_clause="VALUE = 0"
)
o_bud_ostre.save(arcpy.env.workspace + r"\o_K2_budynki_ostre")

# Przekształcenie kryterium lasów na ostre
o_las_ostry = arcpy.ia.Con(
    in_conditional_raster="o_FuzzyMe_Eucptlz",
    in_true_raster_or_constant=0,
    in_false_raster_or_constant=1,
    where_clause="VALUE = 0"
)
o_las_ostry.save(arcpy.env.workspace + r"\o_K3_las_ostry")

# Przekształcenie kryterium nachylenia na ostre
o_nachylenie_ostre = arcpy.ia.Con(
    in_conditional_raster="o_FuzzyMe_Eucpslope",
    in_true_raster_or_constant=0,
    in_false_raster_or_constant=1,
    where_clause="VALUE = 0"
)
o_nachylenie_ostre.save(arcpy.env.workspace + r"\o_K4_nachylenie_ostre")

# Definicja wagi i rastrów wyjściowych z kryteriów
a=1/7
inRaster1 = "o_Fuzzy_wody_pow1"
inRaster2 = "o_FuzzyMe_Euc_bubd"
inRaster3 = "o_FuzzyMe_Eucptlz"
inRaster4="o_FuzzyMe_Euc_roads"
inRaster5="o_FuzzyMe_Eucpslope"
inRaster6="o_FuzzyOv_Fuzz2"
inRaster7="o_FuzzyMe_Con_1"

WSumTableObj = WSTable([[inRaster1, "VALUE", a], [inRaster2, "VALUE", a],
                        [inRaster3, "VALUE", a],[inRaster4, "VALUE", a],
                        [inRaster5, "VALUE", a],
                       [inRaster6, "VALUE", a],[inRaster7, "VALUE", a]])

# Obliczenie ważonej sumy dla jednakowych wag
o_outWeightedSum = WeightedSum(WSumTableObj)
o_outWeightedSum.save(arcpy.env.workspace + r"\o_Weighte_Fuzz1")

# Przypisanie wartości wag z metody AHP
WSumTableObj1 = WSTable([[inRaster1, "VALUE", 0.027], [inRaster2, "VALUE", 0.14],
                        [inRaster3, "VALUE", 0.05],[inRaster4, "VALUE", 0.07],
                        [inRaster5, "VALUE", 0.24],
                       [inRaster6, "VALUE", 0.443],[inRaster7, "VALUE", 0.03]])

# Obliczenie ważonej sumy dla wag z metody AHP
o_outWeightedSumrozwag = WeightedSum(WSumTableObj1)
o_outWeightedSumrozwag.save(arcpy.env.workspace + r"\o_Weighte_Fuzz_rozmyte_z_wagami")

# Łączenie warstw dla jednakowych wag
inRasterList = ["o_K1_rzeki_ostre","o_Weighte_Fuzz1","o_K3_las_ostry","o_K2_budynki_ostre", "o_K4_nachylenie_ostre"]
o_outFzyOverlay = FuzzyOverlay(inRasterList, "AND", 0.9)
o_outFzyOverlay.save(arcpy.env.workspace + r"\o_Teren_przydatnosci")

# Łączenie warstw dla obszaru dla wag z metody AHP
inRasterList1 = ["o_K1_rzeki_ostre","o_Weighte_Fuzz_rozmyte_z_wagami","o_K3_las_ostry","o_K2_budynki_ostre", "o_K4_nachylenie_ostre"]
o_outFzyOverlaywag = FuzzyOverlay(inRasterList1, "AND", 0.9)
o_outFzyOverlaywag.save(arcpy.env.workspace + r"\o_Teren_przydatnosci_wagi")

# Łączenie warstw dla samych kryteriów ostrych
inRasterList2 = ["o_K1_rzeki_ostre","o_K3_las_ostry","o_K2_budynki_ostre", "o_K4_nachylenie_ostre"]
o_outFzyOverlayostre = FuzzyOverlay(inRasterList2, "AND", 0.9)
o_outFzyOverlayostre.save(arcpy.env.workspace + r"\o_Teren_przydatnosci_ostre")

# Definiowanie wartości maksymalnej terenu przydatności dla wersji z jednakowymi wagami
max_value= arcpy.GetRasterProperties_management("o_Teren_przydatnosci", "MAXIMUM")
max_value=float(max_value.getOutput(0).replace(",","."))
print(max_value)

# Definiowanie wartości progowej terenu przydatności
thereshold_value=max_value*0.6
print(thereshold_value)

# Wyznaczanie terenu przydatnego o wartościach powyżej progu
where_clause=f"VALUE >= {thereshold_value}"
o_mapa_przyd = arcpy.ia.Con(
    in_conditional_raster="o_Teren_przydatnosci",
    in_true_raster_or_constant=1,
    in_false_raster_or_constant=0,
    where_clause=where_clause
)
o_mapa_przyd.save(arcpy.env.workspace + r"\o_Wybrany_teren")

# Definiowanie wartości maksymalnej terenu przydatności dla wersji z wagami z metody AHP
max_value1= arcpy.GetRasterProperties_management("o_Teren_przydatnosci_wagi", "MAXIMUM")
max_value1=float(max_value1.getOutput(0).replace(",","."))
print(max_value1)

# Definiowanie wartości progowej terenu przydatności
thereshold_value=max_value1*0.6

# Wyznaczanie terenu przydatnego o wartościach powyżej progu
where_clause=f"VALUE >= {thereshold_value}"
o_mapa_przyd_wagi = arcpy.ia.Con(
    in_conditional_raster="o_Teren_przydatnosci_wagi",
    in_true_raster_or_constant=1,
    in_false_raster_or_constant=0,
    where_clause=where_clause
)
o_mapa_przyd_wagi.save(arcpy.env.workspace + r"\o_Wybrany_teren_wagi")

# Definiowanie wartości maksymalnej terenu przydatności dla wersji ostrych
max_value2= arcpy.GetRasterProperties_management("o_Teren_przydatnosci_ostre", "MAXIMUM")
max_value2=float(max_value2.getOutput(0).replace(",","."))
print(max_value2)

# Definiowanie wartości progowej terenu przydatności
thereshold_value=max_value1*0.6
where_clause=f"VALUE >= {thereshold_value}"

# Wyznaczanie terenu przydatnego o wartościach powyżej progu
o_mapa_przyd_ostre = arcpy.ia.Con(
    in_conditional_raster="o_Teren_przydatnosci_ostre",
    in_true_raster_or_constant=1,
    in_false_raster_or_constant=0,
    where_clause=where_clause
)
o_mapa_przyd_ostre.save(arcpy.env.workspace + r"\o_Wybrany_teren_ostre")


# Kopiowanie warstwy działek
output_layer = arcpy.env.workspace + r"\dzialki_przyciete1"
output_layer2 = arcpy.env.workspace + r"\dzialki_przyciete2"  
arcpy.management.CopyFeatures(dzialki, output_layer)
arcpy.management.CopyFeatures(dzialki, output_layer2)



dzialki1="dzialki_przyciete1"
dzialki2="dzialki_przyciete2"

#WERSJA Z JEDNAKOWYMI WAGAMI
# Zamiana rastra terenu przydatności na poligony
arcpy.conversion.RasterToPolygon(
    in_raster="o_Wybrany_teren",
    out_polygon_features=arcpy.env.workspace + r"\o_Poligon_z_mapy_przydatnosci",
    simplify="SIMPLIFY",
    raster_field="Value",
    create_multipart_features="SINGLE_OUTER_PART",
    max_vertices_per_feature=None
)

#Wybranie poligonów o wartości 1
arcpy.analysis.Select(
    in_features="o_Poligon_z_mapy_przydatnosci",
    out_feature_class=arcpy.env.workspace + r"\o_Raster_value_1",
    where_clause="gridcode = 1"
)

# Przecięcie działek z poligonami
arcpy.analysis.Intersect(
    in_features=f"o_Raster_value_1 #;{dzialki} #",
    out_feature_class=arcpy.env.workspace + r"\o_Intersekcja_dzialki",
    join_attributes="ALL",
    cluster_tolerance=None,
    output_type="INPUT"
)

# Obliczenie powierzchni przecięcia i dodanie do tabeli
arcpy.analysis.Statistics(
    in_table="o_Intersekcja_dzialki",
    out_table=arcpy.env.workspace + r"\o_Intersekcja_dzial_Statistics2",
    statistics_fields="Shape_Area SUM",
    case_field="ID_DZIALKI",
    concatenation_separator=""
)

# Połączenie działek z tabelą statystyczną
arcpy.management.AddJoin(
    in_layer_or_view=dzialki,
    in_field="ID_DZIALKI",
    join_table="o_Intersekcja_dzial_Statistics2",
    join_field="ID_DZIALKI",
    join_type="KEEP_ALL",
    index_join_fields="NO_INDEX_JOIN_FIELDS"
)

# Obliczenie powierzchni nakładania się działki na teren przydatny
arcpy.management.CalculateField(
    in_table=dzialki,
    field="Pow_nakl",
    expression=f"( !o_Intersekcja_dzial_Statistics2.SUM_Shape_Area!/ !{dzialki}.Shape_Area!) * 100",
    expression_type="PYTHON3",
    code_block="",
    field_type="SHORT",
    enforce_domains="NO_ENFORCE_DOMAINS"
)


# Obliczenie powierzchni przyciętej działki i sprawdzenie czy jest 
# równa lub większa od 60% oryginalnej działki
arcpy.management.CalculateField(
    in_table=dzialki,
    field="Przydatnosc_pow_nakl",
    expression=f"!{dzialki}.Pow_nakl!>60",
    expression_type="PYTHON3",
    code_block="",
    field_type="TEXT",
    enforce_domains="NO_ENFORCE_DOMAINS"
)

# Wybranie działek o powierzchni spełniających warunek powyżej 60%
arcpy.management.SelectLayerByAttribute(
    in_layer_or_view=dzialki,
    selection_type="NEW_SELECTION",
    where_clause=f"{dzialki}.Przydatnosc_pow_nakl = '1'",
    invert_where_clause=None
)

wybrane_dzialki = arcpy.env.workspace + r"\o_WybraneDzialki"

# Kopiowanie wybranych działek do nowej klasy obiektów
arcpy.management.CopyFeatures(
    in_features=dzialki,
    out_feature_class=wybrane_dzialki
)

print(f"Wybrane działki zostały zapisane w: {wybrane_dzialki}")

# Wyczyszczenie zaznaczenia
arcpy.management.SelectLayerByAttribute(
    in_layer_or_view=dzialki,
    selection_type="CLEAR_SELECTION"
)

# Agregacja działek w większe obiekty
arcpy.cartography.AggregatePolygons(
    in_features="o_WybraneDzialki",
    out_feature_class=arcpy.env.workspace + r"\o_WybraneDzialki_AggregatePoly",
    aggregation_distance="1 Meters",
    minimum_area="1 SquareMeters",
    minimum_hole_size="1 SquareMeters",
    orthogonality_option="NON_ORTHOGONAL",
    barrier_features=None,
    out_table=arcpy.env.workspace + r"\o_WybraneDzialki_AggregatePoly_Tbl",
    aggregate_field=None
)

# Eksport działek o powierzchni `Shape_Area` > 20000
arcpy.conversion.ExportFeatures(
    in_features="o_WybraneDzialki_AggregatePoly",
    out_features=arcpy.env.workspace + r"\o_WybraneDzialki_ExportFeature1",
    where_clause="Shape_Area > 20000"
)

# Tworzenie prostokątów otaczających działki
arcpy.management.MinimumBoundingGeometry(
    in_features="o_WybraneDzialki_ExportFeature1",
    out_feature_class=arcpy.env.workspace + r"\o_WybraneDzialki_MinimumBoundi",
    geometry_type="RECTANGLE_BY_AREA",
    group_option="NONE",
    group_field=None,
    mbg_fields_option="NO_MBG_FIELDS"
)

input_fc = "o_WybraneDzialki_MinimumBoundi"

# Dodanie nowych pól na szerokość i wysokość
arcpy.AddField_management(input_fc, "Width", "DOUBLE")
arcpy.AddField_management(input_fc, "Height", "DOUBLE")

# Obliczanie szerokości i wysokości
with arcpy.da.UpdateCursor(input_fc, ["SHAPE@", "Width", "Height"]) as cursor:
    for row in cursor:
        extent = row[0].extent
        width = extent.XMax - extent.XMin
        height = extent.YMax - extent.YMin
        row[1] = width  # Szerokość
        row[2] = height  # Wysokość
        cursor.updateRow(row)

# Dodanie obliczonych wartości wysokości i szerokości do warstwy zagregowanych działek
arcpy.management.AddJoin(
    in_layer_or_view="o_WybraneDzialki_AggregatePoly",
    in_field="OBJECTID",
    join_table="o_WybraneDzialki_MinimumBoundi",
    join_field="OBJECTID",
    join_type="KEEP_ALL",
    index_join_fields="NO_INDEX_JOIN_FIELDS"
)

# Eksport zagregowanych działek o szerokości i wysokości większej od 50 m 
# do ostatecznej warstwy działek dla jednakowych wag
arcpy.conversion.ExportFeatures(
    in_features="o_WybraneDzialki_AggregatePoly",
    out_features=arcpy.env.workspace + r"\o_WybraneDzialki1",
    where_clause="o_WybraneDzialki_MinimumBoundi.Width > 50 And o_WybraneDzialki_MinimumBoundi.Height > 50",
    use_field_alias_as_name="NOT_USE_ALIAS"
)

# WERSJA Z WAGAMI Z METODY AHP
# Tworzenie poligonów z rastra terenu przydatności
arcpy.conversion.RasterToPolygon(
    in_raster="o_Wybrany_teren_wagi",
    out_polygon_features=arcpy.env.workspace + r"\o_Poligon_z_mapy_przydatnosci_wagi",
    simplify="SIMPLIFY",
    raster_field="Value",
    create_multipart_features="SINGLE_OUTER_PART",
    max_vertices_per_feature=None
)

# Wybór poligonów o wartości gridcode= 1
arcpy.analysis.Select(
    in_features="o_Poligon_z_mapy_przydatnosci_wagi",
    out_feature_class=arcpy.env.workspace + r"\o_Raster_value_1_wagi",
    where_clause="gridcode = 1"
)

# Przecięcie działek z poligonami
arcpy.analysis.Intersect(
    in_features=f"o_Raster_value_1_wagi #;{dzialki1} #",
    out_feature_class=arcpy.env.workspace + r"\o_Intersekcja_dzialki_wagi",
    join_attributes="ALL",
    cluster_tolerance=None,
    output_type="INPUT"
)

# Obliczenie powierzchni przecięcia i dodanie do tabeli
arcpy.analysis.Statistics(
    in_table="o_Intersekcja_dzialki_wagi",
    out_table=arcpy.env.workspace + r"\o_Intersekcja_dzial_Statistics2_wagi",
    statistics_fields="Shape_Area SUM",
    case_field="ID_DZIALKI",
    concatenation_separator=""
)

# Połączenie działek z tabelą statystyczną
arcpy.management.AddJoin(
    in_layer_or_view=dzialki1,
    in_field="ID_DZIALKI",
    join_table="o_Intersekcja_dzial_Statistics2_wagi",
    join_field="ID_DZIALKI",
    join_type="KEEP_ALL",
    index_join_fields="NO_INDEX_JOIN_FIELDS"
)

# Obliczenie powierzchni nakładania się działki na teren przydatny
arcpy.management.CalculateField(
    in_table=dzialki1,
    field="Pow_nakl",
    expression=f"( !o_Intersekcja_dzial_Statistics2_wagi.SUM_Shape_Area!/ !{dzialki1}.Shape_Area!) * 100",
    expression_type="PYTHON3",
    code_block="",
    field_type="SHORT",
    enforce_domains="NO_ENFORCE_DOMAINS"
)

# Obliczenie powierzchni przyciętej działki i sprawdzenie czy jest 
# równa lubwiększa od 60% oryginalnej działki
arcpy.management.CalculateField(
    in_table=dzialki1,
    field="Przydatnosc_pow_nakl",
    expression=f"!{dzialki1}.Pow_nakl!>60",
    expression_type="PYTHON3",
    code_block="",
    field_type="TEXT",
    enforce_domains="NO_ENFORCE_DOMAINS"
)

# Wybór działek o przydatności powierzchni 60%  
arcpy.management.SelectLayerByAttribute(
    in_layer_or_view=dzialki1,
    selection_type="NEW_SELECTION",
    where_clause=f"{dzialki1}.Przydatnosc_pow_nakl = '1'",
    invert_where_clause=None
)

wybrane_dzialki1 = arcpy.env.workspace + r"\o_WybraneDzialki_wagi"

#  Kopiowanie wybranych działek do nowej klasy obiektów
arcpy.management.CopyFeatures(
    in_features=dzialki1,
    out_feature_class=wybrane_dzialki1
)

print(f"Wybrane działki zostały zapisane w: {wybrane_dzialki1}")
# Wyczyszczenie zaznaczenia
arcpy.management.SelectLayerByAttribute(
    in_layer_or_view=dzialki1,
    selection_type="CLEAR_SELECTION"
)

# Agregacja działek w większe obiekty
arcpy.cartography.AggregatePolygons(
    in_features="o_WybraneDzialki_wagi",
    out_feature_class=arcpy.env.workspace + r"\o_WybraneDzialki_AggregatePoly_wagi",
    aggregation_distance="1 Meters",
    minimum_area="1 SquareMeters",
    minimum_hole_size="1 SquareMeters",
    orthogonality_option="NON_ORTHOGONAL",
    barrier_features=None,
    out_table=arcpy.env.workspace + r"\o_WybraneDzialki_AggregatePoly_Tbl_wagi",
    aggregate_field=None
)
# Eksport działek o powierzchni `Shape_Area` > 20000
arcpy.conversion.ExportFeatures(
    in_features="o_WybraneDzialki_AggregatePoly_wagi",
    out_features=arcpy.env.workspace + r"\o_WybraneDzialki_ExportFeature1_wagi",
    where_clause="Shape_Area > 20000"
)

# Tworzenie prostokątów otaczających działki
arcpy.management.MinimumBoundingGeometry(
    in_features="o_WybraneDzialki_ExportFeature1_wagi",
    out_feature_class=arcpy.env.workspace + r"\o_WybraneDzialki_MinimumBoundi_wagi",
    geometry_type="RECTANGLE_BY_AREA",
    group_option="NONE",
    group_field=None,
    mbg_fields_option="NO_MBG_FIELDS"
)

input_fc = "o_WybraneDzialki_MinimumBoundi_wagi"

# Dodanie nowych pól na szerokość i wysokość
arcpy.AddField_management(input_fc, "Width", "DOUBLE")
arcpy.AddField_management(input_fc, "Height", "DOUBLE")

# Obliczanie szerokości i wysokości
with arcpy.da.UpdateCursor(input_fc, ["SHAPE@", "Width", "Height"]) as cursor:
    for row in cursor:
        extent = row[0].extent
        width = extent.XMax - extent.XMin
        height = extent.YMax - extent.YMin
        row[1] = width  # Szerokość
        row[2] = height  # Wysokość
        cursor.updateRow(row)

# Dodanie obliczonych wartości wysokości i szerokości do warstwy zagregowanych działek
arcpy.management.AddJoin(
    in_layer_or_view="o_WybraneDzialki_AggregatePoly_wagi",
    in_field="OBJECTID",
    join_table="o_WybraneDzialki_MinimumBoundi_wagi",
    join_field="OBJECTID",
    join_type="KEEP_ALL",
    index_join_fields="NO_INDEX_JOIN_FIELDS"
)

# Eksport zagregowanych działek o szerokości i wysokości większej od 50 m
arcpy.conversion.ExportFeatures(
    in_features="o_WybraneDzialki_AggregatePoly_wagi",
    out_features=arcpy.env.workspace + r"\o_WybraneDzialki1_wagi",
    where_clause="o_WybraneDzialki_MinimumBoundi_wagi.Width > 50 And o_WybraneDzialki_MinimumBoundi_wagi.Height > 50",
    use_field_alias_as_name="NOT_USE_ALIAS"
)


# WERSJA OSTRYCH KRYTERIÓW
# Zamiana rastra terenu przydatności na poligony
arcpy.conversion.RasterToPolygon(
    in_raster="o_Wybrany_teren_ostre",
    out_polygon_features=arcpy.env.workspace + r"\o_Poligon_z_mapy_przydatnosci_ostre",
    simplify="SIMPLIFY",
    raster_field="Value",
    create_multipart_features="SINGLE_OUTER_PART",
    max_vertices_per_feature=None
)

# Wybór poligonów o wartości 1
arcpy.analysis.Select(
    in_features="o_Poligon_z_mapy_przydatnosci_ostre",
    out_feature_class=arcpy.env.workspace + r"\o_Raster_value_1_ostre",
    where_clause="gridcode = 1"
)

# Przecięcie działek z poligonami
arcpy.analysis.Intersect(
    in_features=f"o_Raster_value_1_ostre #;{dzialki2} #",
    out_feature_class=arcpy.env.workspace + r"\o_Intersekcja_dzialki_ostre",
    join_attributes="ALL",
    cluster_tolerance=None,
    output_type="INPUT"
)

# Obliczenie powierzchni przecięcia i dodanie do tabeli
arcpy.analysis.Statistics(
    in_table="o_Intersekcja_dzialki_ostre",
    out_table=arcpy.env.workspace + r"\o_Intersekcja_dzial_Statistics2_ostre",
    statistics_fields="Shape_Area SUM",
    case_field="ID_DZIALKI",
    concatenation_separator=""
)

# Połączenie działek z tabelą statystyczną
arcpy.management.AddJoin(
    in_layer_or_view=dzialki2,
    in_field="ID_DZIALKI",
    join_table="o_Intersekcja_dzial_Statistics2_ostre",
    join_field="ID_DZIALKI",
    join_type="KEEP_ALL",
    index_join_fields="NO_INDEX_JOIN_FIELDS"
)

# Obliczenie powierzchni nakładania się działki na teren przydatny
arcpy.management.CalculateField(
    in_table=dzialki2,
    field="Pow_nakl",
    expression=f"( !o_Intersekcja_dzial_Statistics2_ostre.SUM_Shape_Area!/ !{dzialki2}.Shape_Area!) * 100",
    expression_type="PYTHON3",
    code_block="",
    field_type="SHORT",
    enforce_domains="NO_ENFORCE_DOMAINS"
)


# Obliczenie powierzchni przyciętej działki i sprawdzenie czy jest 
# równa lubwiększa od 60% oryginalnej działki
arcpy.management.CalculateField(
    in_table=dzialki2,
    field="Przydatnosc_pow_nakl",
    expression=f"!{dzialki2}.Pow_nakl!>60",
    expression_type="PYTHON3",
    code_block="",
    field_type="TEXT",
    enforce_domains="NO_ENFORCE_DOMAINS"
)

# Wybór działek o przydatności powierzchni 60%
arcpy.management.SelectLayerByAttribute(
    in_layer_or_view=dzialki2,
    selection_type="NEW_SELECTION",
    where_clause=f"{dzialki2}.Przydatnosc_pow_nakl = '1'",
    invert_where_clause=None
)

wybrane_dzialki2 = arcpy.env.workspace + r"\o_WybraneDzialki_ostre"

# Eksport wybranych działek do nowej klasy obiektów
arcpy.management.CopyFeatures(
    in_features=dzialki2,
    out_feature_class=wybrane_dzialki2
)

print(f"Wybrane działki zostały zapisane w: {wybrane_dzialki2}")
# Wyczyszczenie zaznaczenia
arcpy.management.SelectLayerByAttribute(
    in_layer_or_view=dzialki2,
    selection_type="CLEAR_SELECTION"
)

# Agregacja działek w większe obiekty
arcpy.cartography.AggregatePolygons(
    in_features="o_WybraneDzialki_ostre",
    out_feature_class=arcpy.env.workspace + r"\o_WybraneDzialki_AggregatePoly_ostre",
    aggregation_distance="1 Meters",
    minimum_area="1 SquareMeters",
    minimum_hole_size="1 SquareMeters",
    orthogonality_option="NON_ORTHOGONAL",
    barrier_features=None,
    out_table=arcpy.env.workspace + r"\o_WybraneDzialki_AggregatePoly_Tbl_ostre",
    aggregate_field=None
)

# Eksport działek o powierzchni `Shape_Area` > 20000
arcpy.conversion.ExportFeatures(
    in_features="o_WybraneDzialki_AggregatePoly_ostre",
    out_features=arcpy.env.workspace + r"\o_WybraneDzialki_ExportFeature1_ostre",
    where_clause="Shape_Area > 20000"
)

# Tworzenie prostokątów otaczających działki
arcpy.management.MinimumBoundingGeometry(
    in_features="o_WybraneDzialki_ExportFeature1_ostre",
    out_feature_class=arcpy.env.workspace + r"\o_WybraneDzialki_MinimumBoundi_ostre",
    geometry_type="RECTANGLE_BY_AREA",
    group_option="NONE",
    group_field=None,
    mbg_fields_option="NO_MBG_FIELDS"
)

input_fc = "o_WybraneDzialki_MinimumBoundi_ostre"

# Dodanie nowych pól na szerokość i wysokość
arcpy.AddField_management(input_fc, "Width", "DOUBLE")
arcpy.AddField_management(input_fc, "Height", "DOUBLE")

# Obliczanie szerokości i wysokości
with arcpy.da.UpdateCursor(input_fc, ["SHAPE@", "Width", "Height"]) as cursor:
    for row in cursor:
        extent = row[0].extent
        width = extent.XMax - extent.XMin
        height = extent.YMax - extent.YMin
        row[1] = width  # Szerokość
        row[2] = height  # Wysokość
        cursor.updateRow(row)

# Dodanie obliczonych wartości wysokości i szerokości do warstwy zagregowanych działek
arcpy.management.AddJoin(
    in_layer_or_view="o_WybraneDzialki_AggregatePoly_ostre",
    in_field="OBJECTID",
    join_table="o_WybraneDzialki_MinimumBoundi_ostre",
    join_field="OBJECTID",
    join_type="KEEP_ALL",
    index_join_fields="NO_INDEX_JOIN_FIELDS"
)
# Eksport zagregowanych działek o szerokości i wysokości większej od 50 m 
# do ostatecznej warstwy działek dla różnych wag
arcpy.conversion.ExportFeatures(
    in_features="o_WybraneDzialki_AggregatePoly_ostre",
    out_features=arcpy.env.workspace + r"\o_Wybranedzialki1_ostre",
    where_clause="o_WybraneDzialki_MinimumBoundi_ostre.Width > 50 And o_WybraneDzialki_MinimumBoundi_ostre.Height > 50",
    use_field_alias_as_name="NOT_USE_ALIAS"
)



# Łączenie wartw pokrycia terenu 
arcpy.management.Merge(
    inputs=[ptzb, ptwp, ptut, pttr, ptrk, ptpl, ptnz, ptlz, ptkm, ptgn],
    output=arcpy.env.workspace + r"\PT_merge_cliped",
    add_source="NO_SOURCE_INFO"
)

# Funckja przypisująca koszt do typu pokrycia terenu
arcpy.management.CalculateField(
    in_table="PT_merge_cliped",
    field="KOSZT",
    expression="przypisz_koszt(!X_KOD!)",
    expression_type="PYTHON3",
    code_block="""def przypisz_koszt(typ):
    if typ in ['PTWP01', 'PTWP03', 'PTUT01', 'PTKM04', 'PTSO01', 'PTSSO02', 'PTWZ01', 'PTWZ02']:
        return 0  
    elif typ in ['PTWP02','PTZB01','PTZB04', 'PTZB03', 'PTKM02', 'PTKM03']:
        return 200
    elif typ in ['PTNZ01', 'PTNZ02']:
        return 150
    elif typ in ['PTZB02', 'PTLZ01', 'PTUT03', 'PTKM01']:
        return 100
    elif typ == 'PTUT02':
        return 90
    elif typ in ['PTZB05', 'PTLZ02', 'PTLZ03', 'PTPL01']:
        return 50
    elif typ in ['PTUT04', 'PTUT05', 'PTTR01']:
        return 20
    elif typ in ['PTRK01', 'PTRK02']:
        return 15
    elif typ in ['PTTR02', 'PTGN01', 'PTGN02', 'PTGN03', 'PTGN04']:
        return 1
""",
    field_type="SHORT",
    enforce_domains="NO_ENFORCE_DOMAINS"
)

# Zamiana warstwy wektorowej na raster
arcpy.conversion.FeatureToRaster(
    in_features="PT_merge_cliped",
    field="KOSZT",
    out_raster=arcpy.env.workspace + r"\Feature_PT_m1",
    cell_size=arcpy.env.workspace+r"\o_przycietyNMT"
)

# Utworzenie warstwy z kosztami
koszty_null = arcpy.ia.SetNull(
    in_conditional_raster="Feature_PT_m1",
    in_false_raster_or_constant="Feature_PT_m1",
    where_clause="Value = 0"
)
koszty_null.save(arcpy.env.workspace + r"\koszty_null")


# Przycoięcie linii energetycznych do obszaru gminy
arcpy.analysis.Clip(
    in_features=linie_energetyczne,
    clip_features=gmina_bufor,
    out_feature_class=arcpy.env.workspace + r"\linie_energetyczne_Clip",
    cluster_tolerance=None
)

#JEDNAKOWE WAGI
# Sprawdzenie czy warstwa działek ma rekordy
# Jezeli tak to obliczanie kosztu najkrótszej ścieżki
feature_count = int(arcpy.management.GetCount("o_WybraneDzialki1").getOutput(0))
if feature_count > 0:
    distance_raster = arcpy.sa.CostDistance(
        in_source_data="o_WybraneDzialki1",
        in_cost_raster="koszty_null",
        maximum_distance=None,
        out_backlink_raster=arcpy.env.workspace + r"\cost_distance",
        source_cost_multiplier=None,
        source_start_cost=None,
        source_resistance_rate=None,
        source_capacity=None,
        source_direction=""
    )
    distance_raster.save(arcpy.env.workspace + r"\CostDis_Wybr1")

    cost_path = arcpy.sa.CostPath(
        in_destination_data="linie_energetyczne_Clip",
        in_cost_distance_raster="CostDis_Wybr1",
        in_cost_backlink_raster="cost_distance",
        path_type="BEST_SINGLE",
        destination_field="OBJECTID",
        force_flow_direction_convention="INPUT_RANGE"
    )
    cost_path.save(arcpy.env.workspace + r"\CostPat_lini1")
else:
    print("Warstwa 'o_WybraneDzialki1' nie zawiera rekordów. Kod nie został wykonany.")

#Z RÓŻNYMI WAGAMI
# Sprawdzenie czy warstwa działek ma rekordy
# Jezeli tak to obliczanie kosztu najkrótszej ścieżki
feature_count_wagi = int(arcpy.management.GetCount("o_WybraneDzialki1_wagi").getOutput(0))
if feature_count_wagi > 0:
    distance_raster_wagi = arcpy.sa.CostDistance(
        in_source_data="o_WybraneDzialki1_wagi",
        in_cost_raster="koszty_null",
        maximum_distance=None,
        out_backlink_raster=arcpy.env.workspace + r"\cost_distance_wagi",
        source_cost_multiplier=None,
        source_start_cost=None,
        source_resistance_rate=None,
        source_capacity=None,
        source_direction=""
    )
    distance_raster_wagi.save(arcpy.env.workspace + r"\CostDis_Wybr1_wagi")

    # Obliczenie najkrótszej ścieżki kosztu
    cost_path_wagi = arcpy.sa.CostPath(
        in_destination_data="linie_energetyczne_Clip",
        in_cost_distance_raster="CostDis_Wybr1_wagi",
        in_cost_backlink_raster="cost_distance_wagi",
        path_type="BEST_SINGLE",
        destination_field="OBJECTID",
        force_flow_direction_convention="INPUT_RANGE"
    )
    cost_path_wagi.save(arcpy.env.workspace + r"\CostPat_lini1_wagi")
else:
    print("Warstwa 'o_WybraneDzialki1_wagi' nie zawiera rekordów. Kod nie został wykonany.")

# OSTRE
# Sprawdzenie czy warstwa działek ma rekordy
# Jezeli tak to obliczanie kosztu najkrótszej ścieżki
feature_count_ostre = int(arcpy.management.GetCount("o_WybraneDzialki1_ostre").getOutput(0))
if feature_count_ostre > 0:
    distance_raster_ostre = arcpy.sa.CostDistance(
        in_source_data="o_WybraneDzialki1_ostre",
        in_cost_raster="koszty_null",
        maximum_distance=None,
        out_backlink_raster=arcpy.env.workspace + r"\cost_distance_ostre",
        source_cost_multiplier=None,
        source_start_cost=None,
        source_resistance_rate=None,
        source_capacity=None,
        source_direction=""
    )
    distance_raster_ostre.save(arcpy.env.workspace + r"\CostDis_Wybr1_ostre")

    cost_path_ostre = arcpy.sa.CostPath(
        in_destination_data="linie_energetyczne_Clip",
        in_cost_distance_raster="CostDis_Wybr1_ostre",
        in_cost_backlink_raster="cost_distance_ostre",
        path_type="BEST_SINGLE",
        destination_field="OBJECTID",
        force_flow_direction_convention="INPUT_RANGE"
    )
    cost_path_ostre.save(arcpy.env.workspace + r"\CostPat_lini1_ostre")
else:
    print("Warstwa 'o_WybraneDzialki1_ostre' nie zawiera rekordów. Kod nie został wykonany.")



