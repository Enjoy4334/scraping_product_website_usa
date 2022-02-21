import zipfile

from functions import get_file
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium import webdriver


def get_proxies_settings(PROXY_HOST, PROXY_PORT, PROXY_USER, PROXY_PASS):
    # Создание zip файла для добавления прокси с авторизацией

    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version":"22.0.0"
    }
    """

    background_js = """
    var config = {
            mode: "fixed_servers",
            rules: {
            singleProxy: {
                scheme: "http",
                host: "%s",
                port: parseInt(%s)
            },
            bypassList: ["localhost"]
            }
        };

    chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

    function callbackFn(details) {
        return {
            authCredentials: {
                username: "%s",
                password: "%s"
            }
        };
    }

    chrome.webRequest.onAuthRequired.addListener(
                callbackFn,
                {urls: ["<all_urls>"]},
                ['blocking']
    );
    """ % (PROXY_HOST, PROXY_PORT, PROXY_USER, PROXY_PASS)
    pluginfile = 'proxy_auth_plugin.zip'
    with zipfile.ZipFile(pluginfile, 'w') as zp:
        zp.writestr("manifest.json", manifest_json)
        zp.writestr("background.js", background_js)
    return pluginfile

def add_proxies_to_driver(chrome_options):
    capabilities = None
    proxy_str = get_file('proxies.txt')
    proxies = proxy_str.strip().replace("@", ":").replace(":", " ").split()
    if len(proxies) == 4:
        login_port, password_port, ip, http_port = proxies
        current_proxies = {
            "http": f'http://{login_port}:{password_port}@{ip}:{http_port}',
            "https": f'http://{login_port}:{password_port}@{ip}:{http_port}'}
        chrome_options.add_extension(get_proxies_settings(ip, http_port, login_port, password_port))
    elif len(proxies) == 2:
        ip, http_port = proxies
        current_proxies = {
            "http": f"http://{ip}:{http_port}",
            "https": f"http://{ip}:{http_port}"}
        prox = Proxy()
        prox.proxy_type = ProxyType.MANUAL
        prox.http_proxy = f"{ip}:{http_port}"
        prox.socks_proxy = f"{ip}:{http_port}"
        prox.ssl_proxy = f"{ip}:{http_port}"

        capabilities = webdriver.DesiredCapabilities.CHROME
        prox.add_to_capabilities(capabilities)
    else:
        current_proxies = None
        print('[ERROR] Ошибка получения прокси')
    return current_proxies, capabilities