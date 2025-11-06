# Kubernetes Deployment

Этот каталог содержит манифесты для развертывания zbxtg в Kubernetes.

## Быстрый старт

### 1. Создайте namespace (опционально)

```bash
kubectl create namespace zbxtg
kubectl config set-context --current --namespace=zbxtg
```

### 2. Создайте секреты

Скопируйте файл-пример и заполните реальными данными:

```bash
cp secret.yaml.example secret.yaml
# Отредактируйте secret.yaml с вашими данными
vim secret.yaml
```

Или создайте секрет напрямую:

```bash
kubectl create secret generic zbxtg-secrets \
  --from-literal=zabbix-url=https://your-zabbix.com \
  --from-literal=zabbix-api-token=your_token \
  --from-literal=telegram-bot-token=your_bot_token \
  --from-literal=telegram-chat-id=123456789
```

### 3. Создайте ConfigMap

```bash
kubectl apply -f configmap.yaml
```

### 4. Разверните приложение

```bash
kubectl apply -f deployment.yaml
```

### 5. Проверьте статус

```bash
# Проверить pods
kubectl get pods -l app=zbxtg

# Посмотреть логи
kubectl logs -l app=zbxtg -f

# Проверить метрики
kubectl port-forward svc/zbxtg-metrics 9090:9090
# Затем откройте http://localhost:9090/metrics
```

## Компоненты

### deployment.yaml

Основной манифест, содержащий:
- **Deployment**: Определение приложения с репликами, probes, resources
- **Service**: ClusterIP сервис для метрик Prometheus
- **PersistentVolumeClaim**: Хранилище для базы данных SQLite

### configmap.yaml

Конфигурация приложения:
- Интервал опроса
- Уровень логирования
- Минимальная серьезность алертов
- Параметры retry

### secret.yaml.example

Пример секретов (НЕ КОММИТИТЬ С РЕАЛЬНЫМИ ДАННЫМИ!):
- Zabbix credentials
- Telegram токены

## Мониторинг

### Prometheus Integration

Приложение экспортирует метрики на порту 9090. Prometheus автоматически обнаружит метрики благодаря аннотациям:

```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "9090"
  prometheus.io/path: "/metrics"
```

### Grafana Dashboard

После настройки Prometheus, импортируйте Grafana dashboard для визуализации метрик.

## Масштабирование

По умолчанию replicas=1, так как бот работает с одним Chat ID. Если нужно обрабатывать несколько чатов, создайте отдельные deployments:

```bash
# Создайте отдельный deployment для каждого чата
kubectl apply -f deployment-chat1.yaml
kubectl apply -f deployment-chat2.yaml
```

## Обновление

### Rolling Update

```bash
# Обновите образ
kubectl set image deployment/zbxtg zbxtg=zbxtg:v2.1.0

# Или обновите манифест и примените
kubectl apply -f deployment.yaml
```

### Rollback

```bash
# Откатите к предыдущей версии
kubectl rollout undo deployment/zbxtg

# Проверьте историю
kubectl rollout history deployment/zbxtg
```

## Troubleshooting

### Проверка логов

```bash
# Логи текущего pod
kubectl logs -l app=zbxtg --tail=100

# Логи всех pods
kubectl logs -l app=zbxtg --all-containers=true

# Следить за логами
kubectl logs -l app=zbxtg -f
```

### Проверка секретов

```bash
# Проверить, существуют ли секреты
kubectl get secrets zbxtg-secrets

# Посмотреть содержимое (base64 encoded)
kubectl get secret zbxtg-secrets -o yaml

# Декодировать значение
kubectl get secret zbxtg-secrets -o jsonpath='{.data.telegram-chat-id}' | base64 -d
```

### Debug Pod

```bash
# Запустить shell в pod
kubectl exec -it deployment/zbxtg -- /bin/bash

# Проверить переменные окружения
kubectl exec -it deployment/zbxtg -- env | grep ZABBIX

# Проверить файлы
kubectl exec -it deployment/zbxtg -- ls -la /app
```

### События

```bash
# Посмотреть события для troubleshooting
kubectl get events --sort-by='.lastTimestamp'

# События для конкретного pod
kubectl describe pod <pod-name>
```

## Безопасность

### Best Practices

1. **Используйте внешний менеджер секретов**: Вместо хранения секретов в YAML, используйте External Secrets Operator или Sealed Secrets
2. **RBAC**: Создайте отдельный ServiceAccount с минимальными правами
3. **Network Policies**: Ограничьте сетевой доступ
4. **Pod Security**: Включены параметры безопасности (runAsNonRoot, readOnlyRootFilesystem)

### Network Policy Example

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: zbxtg-netpol
spec:
  podSelector:
    matchLabels:
      app: zbxtg
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 443  # HTTPS для Zabbix и Telegram
```

## Ресурсы

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Prometheus Operator](https://prometheus-operator.dev/)
- [External Secrets Operator](https://external-secrets.io/)
