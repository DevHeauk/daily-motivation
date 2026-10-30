import * as Notifications from 'expo-notifications';
import { StatusBar } from 'expo-status-bar';
import { useCallback, useEffect, useState } from 'react';
import { AppState, Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import { fetchTodayQuote, registerDevice } from './src/api';
import CampfireBackground from './src/components/CampfireBackground';
import QuoteFeed from './src/components/QuoteFeed';
import { getPushToken } from './src/push';
import TopicScreen from './src/screens/TopicScreen';
import { getDeviceId, loadTopic, saveTopic } from './src/storage';
import { DailyQuote } from './src/types';

export default function App() {
  const [loaded, setLoaded] = useState(false);
  const [deviceId, setDeviceId] = useState<string | null>(null);
  const [topic, setTopic] = useState<string | null>(null);
  const [picking, setPicking] = useState(false);
  const [quote, setQuote] = useState<DailyQuote | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    Promise.all([getDeviceId(), loadTopic()]).then(([id, saved]) => {
      setDeviceId(id);
      setTopic(saved);
      setLoaded(true);
      // 서버에 기기를 등록해 둔다 (기록이 이 기기 ID로 쌓인다)
      if (saved) registerDevice(id, saved).catch((e) => console.warn('기기 등록 실패', e));
    });
  }, []);

  const refresh = useCallback(async () => {
    if (!topic) return;
    try {
      const next = await fetchTodayQuote(topic);
      setError(false);
      // 같은 날 같은 명언이면 애니메이션을 다시 돌리지 않는다
      setQuote((prev) =>
        prev && prev.date === next.date && prev.topic === next.topic ? prev : next,
      );
    } catch {
      setError(true);
    }
  }, [topic]);

  // 주제가 정해지면 오늘의 명언을 불러오고, 앱 복귀/알림 탭 때마다 다시 확인한다
  useEffect(() => {
    refresh();
    const appState = AppState.addEventListener('change', (state) => {
      if (state === 'active') refresh();
    });
    const tap = Notifications.addNotificationResponseReceivedListener(() => refresh());
    return () => {
      appState.remove();
      tap.remove();
    };
  }, [refresh]);

  const selectTopic = async (next: string) => {
    setTopic(next);
    setPicking(false);
    await saveTopic(next);
    if (!deviceId) return;
    try {
      const token = await getPushToken();
      await registerDevice(deviceId, next, token);
    } catch (e) {
      console.warn('기기 등록 실패', e);
    }
  };

  const showPicker = loaded && (!topic || picking);

  return (
    <SafeAreaProvider>
      <View style={styles.root}>
        <StatusBar style="light" />
        <CampfireBackground />
        <SafeAreaView style={styles.safe}>
          <View style={styles.center}>
            {showPicker && <TopicScreen current={topic} onSelect={selectTopic} />}
            {!showPicker && quote && deviceId && (
              <QuoteFeed key={`${quote.topic}-${quote.date}`} today={quote} deviceId={deviceId} />
            )}
            {!showPicker && error && !quote && (
              <Pressable onPress={refresh}>
                <Text style={styles.message}>명언을 불러오지 못했어요. 눌러서 다시 시도</Text>
              </Pressable>
            )}
          </View>
          {!showPicker && topic && (
            <Pressable onPress={() => setPicking(true)} style={styles.topicButton} hitSlop={12}>
              <Text style={styles.topicText}>{topic} · 주제 바꾸기</Text>
            </Pressable>
          )}
        </SafeAreaView>
      </View>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: '#000',
  },
  safe: {
    flex: 1,
  },
  center: {
    flex: 1,
    justifyContent: 'center',
  },
  message: {
    color: 'rgba(255, 255, 255, 0.8)',
    fontSize: 15,
    textAlign: 'center',
  },
  topicButton: {
    alignSelf: 'center',
    marginBottom: 24,
  },
  topicText: {
    color: 'rgba(255, 255, 255, 0.7)',
    fontSize: 14,
  },
});
