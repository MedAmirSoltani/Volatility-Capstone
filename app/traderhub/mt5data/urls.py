from django.urls import path ,include
from .views import fetch_mt5_15min, fetch_2025_15min, fetch_latest_15min,home,user_login,register,loading,how,about,dashboard,preferences,update_preferences,profile,sentiment_analysis,trading_strategies,allcourses
from django.contrib.auth.views import LogoutView


urlpatterns = [
    path('fetch-15min/', fetch_mt5_15min, name='fetch_mt5_15min'),
    path('fetch-2025/', fetch_2025_15min, name='fetch_2025_15min'),
    path('fetch-latest-15min/', fetch_latest_15min, name='fetch_latest_15min'),
    path('home/', home, name='home'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('register/', register, name='register'),
    path('', user_login, name='login'),
    path('how/', how, name='how'),
    path('about/', about, name='about'),
    path('dashboard/', dashboard, name='dashboard'),
    path('preferences/', preferences, name='preferences'),
    path('update_preferences/', update_preferences, name='update_preferences'),
    path('profile/', profile, name='profile'),
    path('sentiment_analysis/', sentiment_analysis, name='sentiment_analysis'),
    path('trading-strategies/', trading_strategies, name='trading_strategies'),
    path('allcourses/', allcourses, name='allcourses'),
    path('loading/', loading, name='loading'),




    path('portfolio-analysis/', fetch_mt5_15min, name='portfolio_analysis'),
    path('market-insights/', fetch_mt5_15min, name='market_insights'),
    path('sector_details/<str:sector_name>/', fetch_mt5_15min, name='sector_details'),
    path('company_details/<str:company_name>/', fetch_mt5_15min, name='company_details'),
    path('chat/', fetch_mt5_15min, name='chat'),
    path('company_portfolio/<str:company_name>/', fetch_mt5_15min, name='company_portfolio'),
]
