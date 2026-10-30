import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { fetchTopics } from '../api';

type Props = {
  current: string | null;
  onSelect: (topic: string) => void;
};

export default function TopicScreen({ current, onSelect }: Props) {
  const [topics, setTopics] = useState<string[]>([]);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetchTopics()
      .then(setTopics)
      .catch(() => setError(true));
  }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>어떤 이야기를 듣고 싶나요?</Text>
      <Text style={styles.subtitle}>매일 아침, 고른 주제의 명언을 보내드려요.</Text>
      {error && <Text style={styles.subtitle}>주제를 불러오지 못했어요.</Text>}
      {!error && topics.length === 0 && <ActivityIndicator color="#fff" />}
      <View style={styles.list}>
        {topics.map((topic) => (
          <Pressable
            key={topic}
            onPress={() => onSelect(topic)}
            style={({ pressed }) => [
              styles.chip,
              topic === current && styles.chipActive,
              pressed && styles.chipPressed,
            ]}
          >
            <Text style={styles.chipText}>{topic}</Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: 32,
    alignItems: 'center',
  },
  title: {
    color: '#fff',
    fontSize: 24,
    fontWeight: '600',
    textAlign: 'center',
  },
  subtitle: {
    marginTop: 12,
    marginBottom: 32,
    color: 'rgba(255, 255, 255, 0.75)',
    fontSize: 15,
    textAlign: 'center',
  },
  list: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 12,
  },
  chip: {
    paddingVertical: 12,
    paddingHorizontal: 22,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.5)',
    backgroundColor: 'rgba(0, 0, 0, 0.25)',
  },
  chipActive: {
    borderColor: '#ffb066',
    backgroundColor: 'rgba(255, 140, 50, 0.3)',
  },
  chipPressed: {
    opacity: 0.6,
  },
  chipText: {
    color: '#fff',
    fontSize: 17,
  },
});
