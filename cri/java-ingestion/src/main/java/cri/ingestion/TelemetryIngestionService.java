package cri.ingestion;

import org.apache.kafka.clients.consumer.*;
import org.apache.kafka.common.serialization.StringDeserializer;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.time.Duration;
import java.util.Collections;
import java.util.Properties;

public class TelemetryIngestionService {
    public static void main(String[] args) {
        String kafkaBootstrap = System.getenv("KAFKA_BOOTSTRAP_SERVERS");
        if (kafkaBootstrap == null) {
            kafkaBootstrap = "localhost:9092";
        }
        
        String dbUrl = System.getenv("POSTGRES_URL");
        if (dbUrl == null) {
            dbUrl = "jdbc:postgresql://localhost:5432/cri_runtime";
        }
        
        String dbUser = System.getenv("POSTGRES_USER");
        if (dbUser == null) {
            dbUser = "cri_admin";
        }
        
        String dbPass = System.getenv("POSTGRES_PASSWORD");
        if (dbPass == null) {
            dbPass = "supersecret";
        }

        System.out.println("Starting Java Telemetry Ingestion Service...");
        System.out.println("Kafka Broker: " + kafkaBootstrap);
        System.out.println("Database URL: " + dbUrl);

        // 1. Setup database table if not exists
        try (Connection conn = DriverManager.getConnection(dbUrl, dbUser, dbPass)) {
            String sql = "CREATE TABLE IF NOT EXISTS cognitive_events (" +
                         "id SERIAL PRIMARY KEY, " +
                         "event_id VARCHAR(255) NOT NULL, " +
                         "trace_id VARCHAR(255) NOT NULL, " +
                         "agent_id VARCHAR(255) NOT NULL, " +
                         "event_type VARCHAR(255) NOT NULL, " +
                         "payload JSONB NOT NULL, " +
                         "timestamp DOUBLE PRECISION" +
                         ");";
            try (PreparedStatement stmt = conn.prepareStatement(sql)) {
                stmt.execute();
            }
            System.out.println("Postgres telemetry events table verified.");
        } catch (Exception exc) {
            System.err.println("Failed to initialize database connection: " + exc.getMessage());
        }

        // 2. Setup Kafka Consumer Properties
        Properties props = new Properties();
        props.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, kafkaBootstrap);
        props.put(ConsumerConfig.GROUP_ID_CONFIG, "java-telemetry-ingestion-group");
        props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class.getName());
        props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");

        try (KafkaConsumer<String, String> consumer = new KafkaConsumer<>(props)) {
            consumer.subscribe(Collections.singletonList("cognitive-events"));
            System.out.println("Subscribed to Kafka topic: 'cognitive-events'");

            // 3. Poll Loop
            while (true) {
                ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(1000));
                for (ConsumerRecord<String, String> record : records) {
                    String value = record.value();
                    System.out.println("Received event: " + value);
                    
                    // Basic parsing & saving
                    try (Connection conn = DriverManager.getConnection(dbUrl, dbUser, dbPass)) {
                        // We will parse out basic fields from raw JSON
                        // For a robust implementation without heavy libraries like Jackson, we search for fields via regex or basic strings
                        String eventId = extractJsonField(value, "event_id");
                        String traceId = extractJsonField(value, "trace_id");
                        String agentId = extractJsonField(value, "agent_id");
                        String eventType = extractJsonField(value, "event_type");
                        double timestamp = System.currentTimeMillis() / 1000.0;
                        try {
                            timestamp = Double.parseDouble(extractJsonField(value, "timestamp"));
                        } catch (Exception e) {}

                        String insertSql = "INSERT INTO cognitive_events (event_id, trace_id, agent_id, event_type, payload, timestamp) VALUES (?, ?, ?, ?, ?::jsonb, ?)";
                        try (PreparedStatement stmt = conn.prepareStatement(insertSql)) {
                            stmt.setString(1, eventId);
                            stmt.setString(2, traceId);
                            stmt.setString(3, agentId);
                            stmt.setString(4, eventType);
                            stmt.setString(5, value);
                            stmt.setDouble(6, timestamp);
                            stmt.executeUpdate();
                        }
                        System.out.println("Event successfully persisted to Postgres.");
                    } catch (Exception e) {
                        System.err.println("Persistence failure: " + e.getMessage());
                    }
                }
            }
        } catch (Exception exc) {
            System.err.println("Consumer loop terminated with exception: " + exc.getMessage());
        }
    }

    private static String extractJsonField(String json, String field) {
        String pattern = "\"" + field + "\"\\s*:\\s*\"([^\"]*)\"";
        java.util.regex.Pattern r = java.util.regex.Pattern.compile(pattern);
        java.util.regex.Matcher m = r.matcher(json);
        if (m.find()) {
            return m.group(1);
        }
        // numeric values
        pattern = "\"" + field + "\"\\s*:\\s*([0-9.]+)";
        r = java.util.regex.Pattern.compile(pattern);
        m = r.matcher(json);
        if (m.find()) {
            return m.group(1);
        }
        return "unknown";
    }
}
