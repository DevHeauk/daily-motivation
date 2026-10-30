import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Crypto from 'expo-crypto';

const TOPIC_KEY = '@topic';
const DEVICE_ID_KEY = '@device_id';

export function loadTopic(): Promise<string | null> {
  return AsyncStorage.getItem(TOPIC_KEY);
}

export function saveTopic(topic: string): Promise<void> {
  return AsyncStorage.setItem(TOPIC_KEY, topic);
}

// 이 기기를 구분하는 ID. 처음 실행 때 만들어 계속 쓴다
export async function getDeviceId(): Promise<string> {
  const saved = await AsyncStorage.getItem(DEVICE_ID_KEY);
  if (saved) return saved;
  const id = Crypto.randomUUID();
  await AsyncStorage.setItem(DEVICE_ID_KEY, id);
  return id;
}
