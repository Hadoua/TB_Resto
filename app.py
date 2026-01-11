import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

st.set_page_config(layout="centered", page_title="Dashboard Restaurants") # wide

# https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/iframe
st.markdown("""
<style>
    .stCheckbox { padding-top: 25px; }
    iframe { width: 100%; border: 1px solid #e0e0e0; }
    .stDeployButton {display:none;}
</style>
""", unsafe_allow_html=True) # pour pouvoir utiliser du html

# --- CACHE DES DONNÉES ---
@st.cache_data
def load_data():
    try:
        gdf = gpd.read_file("restaurants.geojson")
        return gdf
    except Exception as e:
        return None

df = load_data()

# Colors configuration https://htmlcolorcodes.com/colors/
COLORS_HEX = {
    'darkblue': '#0066A2',   
    'orange': '#F69730',     
    'green': '#72B026',     
    'darkgreen': '#728224',  
    'purple': '#D252B9',     
    'darkpurple': '#5B396B', 
    'cadetblue': '#436978',  
    'lightred': '#FF8E7F',   
    'beige': '#FFCB92',      
    'darkred': '#A23336',    
    'red': '#D63E2A',        
    'blue': '#38AADD',       
    'pink': '#FF91EA',       
    'gray': '#575757',      
    'lightgray': '#A3A3A3',  
    'lightblue': '#8ADAFF'   
}

def get_folium_color(cuisine):
    c = str(cuisine).lower()
    if 'pizza' in c: return 'darkblue'
    if 'burger' in c: return 'orange'
    if 'sandwich' in c: return 'lightblue'
    if 'sushi' in c or 'japonais' in c: return 'green'
    if 'chinois' in c or 'asiatique' in c or 'thaï' in c: return 'darkgreen'
    if 'indien' in c: return 'darkpurple'
    if 'italien' in c: return 'purple'
    if 'français' in c or 'crêpes' in c: return 'cadetblue'
    if 'grec' in c: return 'lightred'
    if 'libanais' in c or 'kebab' in c: return 'beige'
    if 'mexicain' in c: return 'darkred'
    if 'américain' in c: return 'blue'
    if 'steakhouse' in c or 'poulet' in c: return 'red'
    if 'déjeuner' in c: return 'pink'
    if 'terroir' in c: return 'gray'
    return 'lightgray'

# Config des colonnes de filtres 
col_quartier, col_cuisine, col_vegan, col_vege = st.columns([3.5, 3, 1.1, 1.6]) # st.columns(4)

with col_quartier:
    if 'quartier' in df.columns:
        quartiers_dispo = sorted(list(df['quartier'].unique()))
        quartiers_choisies = st.multiselect("Filtrer par quartier", quartiers_dispo)
    else:
        quartiers_choisies = []

with col_cuisine:
    if 'cuisine' in df.columns:
        cuisines_dispo = sorted(list(df['cuisine'].dropna().unique()))
        cuisines_choisies = st.multiselect("Filtrer par type de cuisine", cuisines_dispo)
    else:
        cuisines_choisies = []

with col_vegan:
    has_vegan = st.checkbox("Végan")

with col_vege:
    has_vege = st.checkbox("Végétarien")



# application des filtres
df_filtered = df.copy()

if quartiers_choisies:
    df_filtered = df_filtered[df_filtered['quartier'].isin(quartiers_choisies)]

if cuisines_choisies:
    df_filtered = df_filtered[df_filtered['cuisine'].isin(cuisines_choisies)]

if has_vegan:
    cols_vegan = [c for c in df.columns if 'vegan' in c.lower()]
    if cols_vegan:
        df_filtered = df_filtered[df_filtered[cols_vegan[0]].astype(str).str.lower().isin(['yes', 'only'])]

if has_vege:
    cols_vege = [c for c in df.columns if 'vegetarian' in c.lower()]
    if cols_vege:
        df_filtered = df_filtered[df_filtered[cols_vege[0]].astype(str).str.lower().isin(['yes', 'only'])]

container_map = st.container()
st.divider() # ligne de séparation 
container_table = st.container()


# --- Table ---
with container_table:
    st.subheader("Détails des résultats")
    selected_rows = [] 

    if not df_filtered.empty:
        df_display = df_filtered.drop(columns='geometry').copy()
        df_display['lat'] = df_filtered.geometry.y
        df_display['lon'] = df_filtered.geometry.x
        
        cols_to_show = ['name', 'cuisine', 'phone', 'horaires', 'quartier', 'lat', 'lon']
        
        gb = GridOptionsBuilder.from_dataframe(df_display[cols_to_show])
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=5)
        gb.configure_selection('single', use_checkbox=True)
        gb.configure_column("lat", hide=True)
        gb.configure_column("lon", hide=True)
        gb.configure_column("name", header_name="Restaurant", width=55)
        gb.configure_column("phone", header_name="Téléphone", width=45)
        gb.configure_column("cuisine", header_name="Cuisine", width=45)
        gb.configure_column("horaires", header_name="Horaires", width=95,  wrapText=True, autoHeight=True)
        gb.configure_column("quartier", header_name="Quartier", width=60)
        
        gridOptions = gb.build()

        grid_response = AgGrid(
            df_display[cols_to_show],
            gridOptions=gridOptions,
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            fit_columns_on_grid_load=False,
            height=250,
            theme='streamlit',
            key='grid_restos',
            reload_data=False
        )
        
        raw_selection = grid_response['selected_rows']
        if raw_selection is None:
            selected_rows = []
        else:
            selected_rows = raw_selection
    else:
        st.warning("Aucun résultat.")

# --- CARTE ---
with container_map:
    st.subheader(f"Carte intéractive ({len(df_filtered)} restaurants sélectionnés)")

    zoom_level = 13
    selected_name = None

    if len(selected_rows) > 0:
        selected_row = selected_rows.iloc[0]
        center_lat = selected_row['lat']
        center_lon = selected_row['lon']
        selected_name = selected_row['name']
        zoom_level = 18
    elif not df_filtered.empty:
        center_lat = df_filtered.geometry.y.mean()
        center_lon = df_filtered.geometry.x.mean()
    else:
        center_lat, center_lon = 46.81, -71.22

    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom_level, tiles="OpenStreetMap") # CartoDB positron
    

    for idx, row in df_filtered.iterrows():
        
        name = row.get('name', 'Sans nom')
        phone = row.get('phone')
        hours = row.get('horaires')
        website = row.get('website')
        cuisine_raw = row.get('cuisine', 'Resto')
        cuisine_tag = str(cuisine_raw).upper()
        quartier_display = row.get('quartier', '')
        
        color_name = get_folium_color(cuisine_raw)
        color_hex = COLORS_HEX.get(color_name, '#38AADD')
        text_color = "#8B4513" if color_name == 'beige' else color_hex

        # --- Config POPUP ---
        html_content = f"""
        <div style="font-family: Arial; width: 250px;">
            <h3 style="color: {text_color}; margin: 0 0 5px 0;">{name}</h3>
            <div style="font-size: 11px; color: #888; margin-bottom: 5px;">{quartier_display}</div>
            <span style="background-color: {color_hex}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: bold;">
                {cuisine_tag}
            </span>
        <div style="font-size: 12px; margin-top: 10px; line-height: 1.5;">
        """
        
        # je ne veux pas afficher les infos quand elles sont manquantes
        def is_valid(val):
            return val and str(val).lower() not in ['nan', 'none', '', 'n/a', 'non spécifié']
        
        # Merge every thing togther (couche par couche)
        if is_valid(hours):
            html_content += f"🕒 {hours}<br>"
            
        if is_valid(phone):
            html_content += f"📞 {phone}<br>"
            
        if is_valid(website):
            html_content += f"""
            Site web <a href="{website}" target="_blank" style="color: {text_color}; font-weight: bold; text-decoration: underline; word-wrap: break-word;">
                {website}
            </a>
            """
            
        html_content += "</div></div>"

        is_selected = (selected_name is not None and name == selected_name)
        icon_color = "red" if is_selected else color_name

        marker = folium.Marker(
            location=[row.geometry.y, row.geometry.x],
            popup=folium.Popup(html_content, max_width=200),
            tooltip=None,
            icon=folium.Icon(color=icon_color, icon="cutlery", prefix='fa')
        )
        marker.add_to(m)

        if is_selected:
            script = folium.Element(f"""
                <script>
                    function openPopup_{idx}() {{
                        var marker = {marker.get_name()};
                        marker.openPopup();
                    }}
                    setTimeout(openPopup_{idx}, 500); 
                </script>
            """)
            m.get_root().html.add_child(script)

    st_data = st_folium(m, width="100%", height=500, returned_objects=[])
