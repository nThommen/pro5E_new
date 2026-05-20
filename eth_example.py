import geopandas as gpd
import pandapower as pp

lv_grid = pp.from_excel('1055-1_0_4_grid.xlsx')
pp.plotting.plotly.simple_plotly(lv_grid)
pp.runpp(lv_grid)