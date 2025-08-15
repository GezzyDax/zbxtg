#!/bin/bash
# Скрипт для установки SSL сертификатов в системный trust store

set -e  # Остановить выполнение при ошибке

echo "🔐 Установка SSL сертификатов в системный trust store..."

# Проверяем, что мы запущены от root
if [[ $EUID -ne 0 ]]; then
   echo "❌ Этот скрипт должен быть запущен от root (используйте sudo)"
   exit 1
fi

# Определяем путь к директории проекта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Проверяем наличие сертификатов в папке ssl-certs
SSL_CERTS_DIR="$SCRIPT_DIR/ssl-certs"

if [[ ! -d "$SSL_CERTS_DIR" ]]; then
    echo "❌ Директория ssl-certs/ не найдена"
    echo "Поместите ваши SSL сертификаты в папку ssl-certs/"
    exit 1
fi

# Ищем сертификаты в папке ssl-certs
CA_CERT=$(find "$SSL_CERTS_DIR" -name "*CA*" -o -name "*ca*" | head -1)
SERVER_CERT=$(find "$SSL_CERTS_DIR" -name "*.crt" -o -name "*.pem" | grep -v -i ca | head -1)

if [[ -z "$CA_CERT" ]]; then
    echo "❌ Корневой CA сертификат не найден в ssl-certs/"
    echo "Поместите корневой сертификат в ssl-certs/"
    exit 1
fi

if [[ -z "$SERVER_CERT" ]]; then
    echo "❌ Сертификат сервера не найден в ssl-certs/"
    echo "Поместите сертификат сервера в ssl-certs/"
    exit 1
fi

echo "📋 Найден CA сертификат: $(basename "$CA_CERT")"
echo "📋 Найден сертификат сервера: $(basename "$SERVER_CERT")"

# Определяем систему и устанавливаем сертификаты
if [[ -f /etc/arch-release ]]; then
    echo "🐧 Обнаружена Arch Linux"
    
    # Копируем сертификаты в trust store
    echo "📋 Копируем корневой сертификат CA..."
    cp "$CA_CERT" "/etc/ca-certificates/trust-source/anchors/$(basename "$CA_CERT").crt"
    
    echo "📋 Копируем сертификат сервера..."
    cp "$SERVER_CERT" "/etc/ca-certificates/trust-source/anchors/$(basename "$SERVER_CERT").crt"
    
    # Обновляем trust store
    echo "🔄 Обновляем системный trust store..."
    trust extract-compat
    
    echo "✅ Сертификаты успешно установлены в Arch Linux trust store"
    
elif [[ -f /etc/debian_version ]] || [[ -f /etc/ubuntu_version ]]; then
    echo "🐧 Обнаружена Debian/Ubuntu"
    
    # Копируем сертификаты
    echo "📋 Копируем корневой сертификат CA..."
    cp "$CA_CERT" "/usr/local/share/ca-certificates/$(basename "$CA_CERT").crt"
    
    echo "📋 Копируем сертификат сервера..."
    cp "$SERVER_CERT" "/usr/local/share/ca-certificates/$(basename "$SERVER_CERT").crt"
    
    # Обновляем trust store
    echo "🔄 Обновляем системный trust store..."
    update-ca-certificates
    
    echo "✅ Сертификаты успешно установлены в Debian/Ubuntu trust store"
    
elif [[ -f /etc/redhat-release ]] || [[ -f /etc/centos-release ]]; then
    echo "🐧 Обнаружена Red Hat/CentOS"
    
    # Копируем сертификаты
    echo "📋 Копируем корневой сертификат CA..."
    cp "$CA_CERT" "/etc/pki/ca-trust/source/anchors/$(basename "$CA_CERT").crt"
    
    echo "📋 Копируем сертификат сервера..."
    cp "$SERVER_CERT" "/etc/pki/ca-trust/source/anchors/$(basename "$SERVER_CERT").crt"
    
    # Обновляем trust store
    echo "🔄 Обновляем системный trust store..."
    update-ca-trust extract
    
    echo "✅ Сертификаты успешно установлены в Red Hat/CentOS trust store"
    
else
    echo "❌ Неподдерживаемая операционная система"
    echo "Поддерживаются: Arch Linux, Debian/Ubuntu, Red Hat/CentOS"
    exit 1
fi

echo ""
echo "🎉 Установка завершена!"
echo "Теперь вы можете использовать ZABBIX_SSL_VERIFY=true в вашем боте"
echo ""
echo "📝 Убедитесь, что ваши SSL сертификаты находятся в папке ssl-certs/"