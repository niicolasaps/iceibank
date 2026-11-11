import 'package:flutter/material.dart';

/// Paleta visual e componentes base do ICEIBank Mobile — espelhando 1:1 o design
/// Dark Navy & Gold Glassmorphism do frontend web (`frontend/src/App.css`).
class IceiTheme {
  // Cores base (identicas ao App.css)
  static const Color bgDeep = Color(0xFF080F1A);
  static const Color bgMid = Color(0xFF0D1825);
  static const Color bgDark2 = Color(0xFF091220);
  static const Color heroStart = Color(0xFF111F35);
  static const Color heroEnd = Color(0xFF1A3050);

  static const Color gold = Color(0xFFD4AF37);
  static const Color goldBright = Color(0xFFF0D060);
  static const Color goldDark = Color(0xFFB8962E);
  static const Color textPrimary = Color(0xFFF1F5F9);
  static const Color textMuted = Color(0x8CF1F5F9); // ~55%
  static const Color textSubtle = Color(0x66F1F5F9); // ~40%

  static const Color greenStart = Color(0xFF059669);
  static const Color greenEnd = Color(0xFF047857);
  static const Color emerald = Color(0xFF10B981);
  static const Color emeraldLight = Color(0xFF6EE7B7);

  static const Color redStart = Color(0xFFDC2626);
  static const Color redEnd = Color(0xFFB91C1C);
  static const Color danger = Color(0xFFEF4444);
  static const Color dangerLight = Color(0xFFFCA5A5);

  static const Color purpleStart = Color(0xFF7C3AED);
  static const Color purpleEnd = Color(0xFF6D28D9);
  static const Color purpleLight = Color(0xFFC4B5FD);

  static const Color amber = Color(0xFFF59E0B);
  static const Color amberLight = Color(0xFFFDE68A);

  static const Color cardFill = Color(0x0AFFFFFF); // rgba(255,255,255,0.04)
  static const Color cardBorder = Color(0x14FFFFFF); // rgba(255,255,255,0.08)
  static const Color inputFill = Color(0x0DFFFFFF); // rgba(255,255,255,0.05)
  static const Color inputBorder = Color(0x1AFFFFFF); // rgba(255,255,255,0.10)

  // Gradientes
  static const LinearGradient goldGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [gold, goldBright, Color(0xFFC9A227)],
  );

  static const LinearGradient goldBtnGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [gold, goldDark],
  );

  static const LinearGradient greenBtnGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [greenStart, greenEnd],
  );

  static const LinearGradient redBtnGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [redStart, redEnd],
  );

  static const LinearGradient purpleBtnGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [purpleStart, purpleEnd],
  );

  static const LinearGradient pageBgGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [bgDeep, bgMid, bgDark2],
    stops: [0.0, 0.6, 1.0],
  );

  static const LinearGradient heroGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [heroStart, heroEnd],
  );

  static ThemeData buildTheme() {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: bgDeep,
      colorScheme: const ColorScheme.dark(
        primary: gold,
        secondary: goldBright,
        surface: bgMid,
        error: danger,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: Color(0xCC080F1A),
        foregroundColor: textPrimary,
        elevation: 0,
        scrolledUnderElevation: 0,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: inputFill,
        hintStyle: const TextStyle(color: Color(0x40F1F5F9), fontSize: 14),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: inputBorder, width: 1),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: gold, width: 1.5),
        ),
      ),
    );
  }
}

/// Texto com gradiente dourado identico ao `.login-title` e `.brand-name` do web.
class GoldGradientText extends StatelessWidget {
  final String text;
  final TextStyle style;
  const GoldGradientText(this.text, {super.key, required this.style});

  @override
  Widget build(BuildContext context) {
    return ShaderMask(
      blendMode: BlendMode.srcIn,
      shaderCallback: (bounds) =>
          IceiTheme.goldGradient.createShader(Rect.fromLTWH(0, 0, bounds.width, bounds.height)),
      child: Text(text, style: style),
    );
  }
}

/// Label em caixa alta estilo `.form-label` da web.
class FormLabel extends StatelessWidget {
  final String text;
  const FormLabel(this.text, {super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 7),
      child: Text(
        text.toUpperCase(),
        style: const TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w700,
          color: Color(0x80F1F5F9),
          letterSpacing: 1.3,
        ),
      ),
    );
  }
}

/// Botao com gradiente e sombra brilhante (`.btn-gold`, `.btn-green`, `.btn-red`, `.btn-purple`).
class GradientButton extends StatelessWidget {
  final String label;
  final String? emoji;
  final LinearGradient gradient;
  final Color textColor;
  final Color glowColor;
  final VoidCallback? onPressed;
  final bool loading;
  final double verticalPadding;

  const GradientButton({
    super.key,
    required this.label,
    this.emoji,
    required this.gradient,
    this.textColor = Colors.white,
    required this.glowColor,
    required this.onPressed,
    this.loading = false,
    this.verticalPadding = 14,
  });

  @override
  Widget build(BuildContext context) {
    final disabled = onPressed == null || loading;
    return Opacity(
      opacity: disabled ? 0.5 : 1.0,
      child: Container(
        decoration: BoxDecoration(
          gradient: gradient,
          borderRadius: BorderRadius.circular(10),
          boxShadow: disabled
              ? null
              : [
                  BoxShadow(
                    color: glowColor.withValues(alpha: 0.32),
                    blurRadius: 20,
                    offset: const Offset(0, 4),
                  ),
                ],
        ),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            borderRadius: BorderRadius.circular(10),
            onTap: disabled ? null : onPressed,
            child: Padding(
              padding: EdgeInsets.symmetric(vertical: verticalPadding, horizontal: 16),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  if (loading) ...[
                    SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2, color: textColor),
                    ),
                    const SizedBox(width: 8),
                  ] else if (emoji != null) ...[
                    Text(emoji!, style: const TextStyle(fontSize: 15)),
                    const SizedBox(width: 7),
                  ],
                  Flexible(
                    child: Text(
                      label,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: textColor,
                        fontWeight: FontWeight.w700,
                        fontSize: 14.5,
                        letterSpacing: 0.2,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Card translucido estilo glassmorphism (`.card` do App.css).
class GlassCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry padding;
  final Color? borderColor;
  final Color? backgroundColor;

  const GlassCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(20),
    this.borderColor,
    this.backgroundColor,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: backgroundColor ?? IceiTheme.cardFill,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: borderColor ?? IceiTheme.cardBorder, width: 1),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.3),
            blurRadius: 30,
            offset: const Offset(0, 14),
          ),
        ],
      ),
      child: child,
    );
  }
}

/// Banner de alerta estilo `.alert-error` / `.alert-success` da web.
class IceiAlert extends StatelessWidget {
  final String texto;
  final bool erro;
  final VoidCallback? onClose;

  const IceiAlert({super.key, required this.texto, this.erro = true, this.onClose});

  @override
  Widget build(BuildContext context) {
    final bg = erro ? const Color(0x1AEF4444) : const Color(0x1A10B981);
    final border = erro ? const Color(0x40EF4444) : const Color(0x4010B981);
    final fg = erro ? IceiTheme.dangerLight : IceiTheme.emeraldLight;
    final icon = erro ? '⚠️' : '✅';

    return Container(
      margin: const EdgeInsets.only(top: 12),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: bg,
        border: Border.all(color: border),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(icon, style: const TextStyle(fontSize: 15)),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              texto,
              style: TextStyle(color: fg, fontSize: 13.5, fontWeight: FontWeight.w500, height: 1.35),
            ),
          ),
          if (onClose != null)
            GestureDetector(
              onTap: onClose,
              child: Padding(
                padding: const EdgeInsets.only(left: 8),
                child: Text('✕', style: TextStyle(color: fg.withValues(alpha: 0.7), fontSize: 14)),
              ),
            ),
        ],
      ),
    );
  }
}

