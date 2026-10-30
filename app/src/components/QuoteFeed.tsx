import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import {
  Animated,
  GestureResponderEvent,
  PanResponder,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from 'react-native';
import { fetchNextQuote, recordView } from '../api';
import { Quote } from '../types';
import QuoteSlide from './QuoteSlide';

// 오늘의 명언에서 시작해, 위로 스와이프하면 같은 주제의 새 명언, 아래로 스와이프하면 이전 명언을 보여준다
type Props = {
  today: Quote;
  deviceId: string;
};

export default function QuoteFeed({ today, deviceId }: Props) {
  const { height } = useWindowDimensions();
  const [quotes, setQuotes] = useState<Quote[]>([today]);
  const [index, setIndex] = useState(0);
  const [from, setFrom] = useState<'below' | 'above'>('below');
  const drag = useRef(new Animated.Value(0)).current;
  const loading = useRef(false);

  const loadMore = useCallback(async () => {
    if (loading.current) return;
    loading.current = true;
    try {
      // 이미 본 명언은 서버가 기록으로 제외하므로, 아직 안 보여준 것만 넘긴다
      const pending = quotes.slice(index + 1).map((q) => q.id);
      const next = await fetchNextQuote(today.topic, deviceId, [today.id, ...pending]);
      setQuotes((prev) => (prev.some((q) => q.id === next.id) ? prev : [...prev, next]));
    } catch (e) {
      console.warn('다음 명언 불러오기 실패', e);
    } finally {
      loading.current = false;
    }
  }, [today.topic, today.id, deviceId, quotes, index]);

  // 화면에 처음 나온 명언을 서버에 기록한다 (이전 명언으로 돌아간 것은 다시 기록하지 않는다)
  const recorded = useRef(new Set<string>());
  useEffect(() => {
    const id = quotes[index].id;
    if (recorded.current.has(id)) return;
    recorded.current.add(id);
    recordView(deviceId, id, index === 0 ? 'today' : 'swipe').catch((e) =>
      console.warn('조회 기록 실패', e),
    );
  }, [index]);

  // 다음 명언을 미리 받아 둔다
  useEffect(() => {
    if (index >= quotes.length - 1) loadMore();
  }, [index, quotes.length, loadMore]);

  // 새 명언이 그려진 뒤에 위치를 되돌린다. 밀어낸 직후 되돌리면 이전 명언이 한 프레임 깜빡인다
  useLayoutEffect(() => {
    drag.setValue(0);
  }, [index, drag]);

  const settle = () => Animated.spring(drag, { toValue: 0, useNativeDriver: true }).start();

  // 현재 명언을 dir 방향(-1 위, 1 아래)으로 밀어낸 뒤 다음 화면으로 바꾼다
  const slideOut = (dir: -1 | 1, after: () => void) => {
    Animated.timing(drag, {
      toValue: dir * height * 0.5,
      duration: 250,
      useNativeDriver: true,
    }).start(() => {
      after();
    });
  };

  const goNext = () => {
    if (!quotes[index + 1]) {
      loadMore();
      settle();
      return;
    }
    slideOut(-1, () => {
      setFrom('below');
      setIndex((i) => i + 1);
    });
  };

  const goPrev = () => {
    if (index === 0) {
      settle();
      return;
    }
    slideOut(1, () => {
      setFrom('above');
      setIndex((i) => i - 1);
    });
  };

  // PanResponder는 한 번만 만들어지므로 최신 상태를 ref로 참조한다
  const latest = useRef({ goNext, goPrev, index });
  latest.current = { goNext, goPrev, index };

  // PanResponder의 gestureState(dy)는 주제 선택 직후 0으로 고정되는 경우가 있어
  // 터치 시작 좌표를 직접 기록해 이동 거리를 계산한다
  const touchStart = useRef({ y: 0, t: 0 });
  const dyOf = (e: GestureResponderEvent) => e.nativeEvent.pageY - touchStart.current.y;
  // 첫 명언에서는 아래로 끌 수 없게 막는다
  const clampDy = (dy: number) => (latest.current.index === 0 ? Math.min(0, dy) : dy);

  const pan = useRef(
    PanResponder.create({
      onStartShouldSetPanResponderCapture: (e) => {
        touchStart.current = { y: e.nativeEvent.pageY, t: e.nativeEvent.timestamp };
        return false;
      },
      onMoveShouldSetPanResponder: (e) => Math.abs(clampDy(dyOf(e))) > 10,
      onPanResponderMove: (e) => drag.setValue(clampDy(dyOf(e))),
      onPanResponderRelease: (e) => {
        const dy = clampDy(dyOf(e));
        const quick = e.nativeEvent.timestamp - touchStart.current.t < 250;
        if (dy < -80 || (quick && dy < -30)) {
          latest.current.goNext();
        } else if (dy > 80 || (quick && dy > 30)) {
          latest.current.goPrev();
        } else {
          settle();
        }
      },
      onPanResponderTerminate: () => settle(),
    }),
  ).current;

  const opacity = drag.interpolate({
    inputRange: [-height * 0.5, 0, height * 0.5],
    outputRange: [0, 1, 0],
    extrapolate: 'clamp',
  });

  return (
    <View style={styles.container} {...pan.panHandlers}>
      <Animated.View style={{ opacity, transform: [{ translateY: drag }] }}>
        <QuoteSlide key={quotes[index].id} quote={quotes[index]} from={from} />
      </Animated.View>
      {index === 0 && <Text style={styles.hint}>위로 밀어 다른 명언 보기</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
  },
  hint: {
    position: 'absolute',
    bottom: 16,
    alignSelf: 'center',
    color: 'rgba(255, 255, 255, 0.5)',
    fontSize: 13,
  },
});
